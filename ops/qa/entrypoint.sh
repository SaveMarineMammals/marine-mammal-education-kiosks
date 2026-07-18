#!/usr/bin/env bash
# Headless Xibo Linux Player entrypoint for ephemeral visual QA.
# Critical: this process must NEVER exit while the QA pipeline needs captures.
# The snap player often crashes under Docker/Xvfb; we keep Xvfb (+ optional
# fallback renderer) alive regardless.
set -uo pipefail

DISPLAY_NUM="${DISPLAY_NUM:-99}"
export DISPLAY=":${DISPLAY_NUM}"
SCREEN_GEOMETRY="${SCREEN_GEOMETRY:-1920x1080x24}"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-/artifacts}"
PLAYER_ROOT="${PLAYER_ROOT:-/opt/xibo-player}"
PLAYER_BIN="${PLAYER_BIN:-${PLAYER_ROOT}/bin/player}"
WATCHDOG_BIN="${WATCHDOG_BIN:-${PLAYER_ROOT}/bin/watchdog}"
SNAP_RUN="${SNAP_RUN:-${PLAYER_ROOT}/bin/snap_run.sh}"
CMS_URL="${XIBO_CMS_URL:-http://cms-web}"
CMS_KEY="${XIBO_CMS_KEY:-}"
DISPLAY_NAME="${XIBO_DISPLAY_NAME:-qa-kiosk-01}"
HARDWARE_KEY="${XIBO_HARDWARE_KEY:-qa-kiosk-01-hw}"
PLAYER_CONFIG_DIR="${PLAYER_CONFIG_DIR:-/var/lib/xibo-player}"
PLAYER_LIBRARY_DIR="${PLAYER_LIBRARY_DIR:-${PLAYER_CONFIG_DIR}/library}"
PREVIEW_IMAGE="${PREVIEW_IMAGE:-${PLAYER_CONFIG_DIR}/preview.png}"
TIMELINE_PREVIEW_HTML="${TIMELINE_PREVIEW_HTML:-${PLAYER_CONFIG_DIR}/timeline-preview/index.html}"
XVFB_LOG="${ARTIFACTS_DIR}/xvfb.log"
PLAYER_LOG="${ARTIFACTS_DIR}/player.log"
FALLBACK_LOG="${ARTIFACTS_DIR}/fallback-renderer.log"
RUNNING=1

export SNAP="${SNAP:-${PLAYER_ROOT}}"
export SNAP_NAME="${SNAP_NAME:-xibo-player}"
export SNAP_USER_COMMON="${SNAP_USER_COMMON:-${PLAYER_CONFIG_DIR}}"
export SNAP_USER_DATA="${SNAP_USER_DATA:-${PLAYER_CONFIG_DIR}}"
export HOME="${HOME:-/root}"

mkdir -p "${ARTIFACTS_DIR}" "${PLAYER_CONFIG_DIR}" "${PLAYER_LIBRARY_DIR}" \
  "${HOME}/snap/xibo-player/common"

if [[ -f "${PLAYER_CONFIG_DIR}/snap-common/cmsSettings.xml" ]]; then
  cp -f "${PLAYER_CONFIG_DIR}/snap-common/cmsSettings.xml" \
    "${HOME}/snap/xibo-player/common/cmsSettings.xml"
fi

log() {
  printf '[entrypoint] %s\n' "$*"
}

cleanup() {
  RUNNING=0
  log "Shutting down player stack"
  jobs -p | xargs -r kill 2>/dev/null || true
  if [[ -n "${XVFB_PID:-}" ]] && kill -0 "${XVFB_PID}" 2>/dev/null; then
    kill "${XVFB_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

rm -f "/tmp/.X${DISPLAY_NUM}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM}" 2>/dev/null || true

log "Starting Xvfb on DISPLAY=${DISPLAY} (${SCREEN_GEOMETRY})"
Xvfb "${DISPLAY}" -screen 0 "${SCREEN_GEOMETRY}" -ac -nolisten tcp >"${XVFB_LOG}" 2>&1 &
XVFB_PID=$!

for _ in $(seq 1 30); do
  if xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if ! xdpyinfo -display "${DISPLAY}" >/dev/null 2>&1; then
  log "ERROR: Xvfb failed to start; see ${XVFB_LOG}"
  exit 1
fi

xset -display "${DISPLAY}" s off 2>/dev/null || true
xset -display "${DISPLAY}" -dpms 2>/dev/null || true
xset -display "${DISPLAY}" s noblank 2>/dev/null || true
if command -v xsetroot >/dev/null 2>&1; then
  xsetroot -display "${DISPLAY}" -solid "#102a43"
fi

write_player_config() {
  local cms_xml="${SNAP_USER_COMMON}/cmsSettings.xml"
  local home_xml="${HOME}/snap/xibo-player/common/cmsSettings.xml"
  local player_xml="${SNAP_USER_COMMON}/playerSettings.xml"

  if [[ -z "${CMS_KEY}" && -f "${cms_xml}" ]]; then
    if grep -q "<key>[^<]\+</key>" "${cms_xml}"; then
      log "Preserving existing cmsSettings.xml (XIBO_CMS_KEY unset)"
      return
    fi
  fi

  cat >"${cms_xml}" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<cmsSettings>
  <cmsAddress>${CMS_URL}</cmsAddress>
  <key>${CMS_KEY}</key>
  <localLibrary>${PLAYER_LIBRARY_DIR}</localLibrary>
  <displayId>${HARDWARE_KEY}</displayId>
</cmsSettings>
EOF
  cp -f "${cms_xml}" "${home_xml}"

  cat >"${player_xml}" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<playerSettings>
  <displayName>${DISPLAY_NAME}</displayName>
  <sizeX>1920</sizeX>
  <sizeY>1080</sizeY>
  <offsetX>0</offsetX>
  <offsetY>0</offsetY>
  <preventSleep>true</preventSleep>
</playerSettings>
EOF

  cat >"${PLAYER_CONFIG_DIR}/config.json" <<EOF
{
  "cmsAddress": "${CMS_URL}",
  "cmsKey": "${CMS_KEY}",
  "displayName": "${DISPLAY_NAME}",
  "displayId": "${HARDWARE_KEY}"
}
EOF
  log "Wrote cmsSettings.xml (key_len=${#CMS_KEY}) at ${cms_xml}"
}

write_player_config

export GST_PLUGIN_PATH="${SNAP}/usr/lib/gstreamer-1.0${GST_PLUGIN_PATH:+:$GST_PLUGIN_PATH}"
export GST_PLUGIN_SYSTEM_PATH="${SNAP}/usr/lib/gstreamer-1.0"
export GST_PLUGIN_SCANNER="${SNAP}/usr/libexec/gstreamer-1.0/gst-plugin-scanner"
export LD_LIBRARY_PATH="${SNAP}/usr/lib:${SNAP}/lib:${SNAP}/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
export PATH="${SNAP}/bin:${PATH}"

start_timeline_preview() {
  if [[ ! -f "${TIMELINE_PREVIEW_HTML}" ]]; then
    return 1
  fi
  local browser=""
  if command -v chromium-browser >/dev/null 2>&1; then
    browser="$(command -v chromium-browser)"
  elif command -v chromium >/dev/null 2>&1; then
    browser="$(command -v chromium)"
  elif command -v google-chrome >/dev/null 2>&1; then
    browser="$(command -v google-chrome)"
  else
    log "Timeline preview HTML present but Chromium is not installed"
    return 1
  fi
  log "Starting Chromium timeline preview: ${TIMELINE_PREVIEW_HTML}"
  mkdir -p /tmp/chrome-qa-profile
  # file:// URL; no sandbox required inside privileged QA container.
  # Skip first-run / default-browser prompts that otherwise block the stage.
  "${browser}" \
    --no-sandbox \
    --disable-gpu \
    --disable-dev-shm-usage \
    --disable-software-rasterizer \
    --allow-file-access-from-files \
    --no-first-run \
    --no-default-browser-check \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-features=TranslateUI \
    --check-for-update-interval=31536000 \
    --user-data-dir=/tmp/chrome-qa-profile \
    --hide-scrollbars \
    --window-position=0,0 \
    --window-size=1920,1080 \
    --start-fullscreen \
    --kiosk \
    "file://${TIMELINE_PREVIEW_HTML}" \
    >>"${FALLBACK_LOG}" 2>&1 &
  return 0
}

start_fallback_renderer() {
  if start_timeline_preview; then
    return
  fi
  if [[ ! -f "${PREVIEW_IMAGE}" ]]; then
    log "No timeline preview or preview image; drawing solid Xvfb background only"
    return
  fi
  if command -v feh >/dev/null 2>&1; then
    log "Starting feh fallback renderer with ${PREVIEW_IMAGE}"
    feh --fullscreen --auto-zoom --reload 5 "${PREVIEW_IMAGE}" >>"${FALLBACK_LOG}" 2>&1 &
    return
  fi
  log "No feh available for static preview fallback"
}

# Prefer animated timeline preview; fall back to static feh when missing.
start_fallback_renderer

player_supervisor() {
  local attempts=0
  if [[ ! -x "${PLAYER_BIN}" ]]; then
    log "Xibo player binary missing (${PLAYER_BIN}); relying on fallback renderer"
    return
  fi
  while [[ "${RUNNING}" -eq 1 ]]; do
    attempts=$((attempts + 1))
    log "Launching Xibo Linux Player attempt=${attempts}"
    if [[ -x "${SNAP_RUN}" && -x "${PLAYER_BIN}" ]]; then
      # Prefer the player binary directly; watchdog exit was crash-looping the container.
      "${SNAP_RUN}" "${PLAYER_BIN}" >>"${PLAYER_LOG}" 2>&1 &
    else
      "${PLAYER_BIN}" >>"${PLAYER_LOG}" 2>&1 &
    fi
    local pid=$!
    wait "${pid}" || true
    log "Player exited; see ${PLAYER_LOG}"
    if [[ "${attempts}" -ge 3 ]]; then
      log "Giving up on Xibo player after ${attempts} attempts; Xvfb/fallback remain up"
      break
    fi
    sleep 3
  done
}

player_supervisor &

log "Ready for capture via scrot/ffmpeg on DISPLAY=${DISPLAY}"
# Keep the container PID 1 alive for docker exec captures.
while [[ "${RUNNING}" -eq 1 ]]; do
  if ! kill -0 "${XVFB_PID}" 2>/dev/null; then
    log "Xvfb died; exiting"
    exit 1
  fi
  sleep 5
done
