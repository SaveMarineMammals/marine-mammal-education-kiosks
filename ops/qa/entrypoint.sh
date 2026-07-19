#!/usr/bin/env bash
# Headless Xibo Linux Player entrypoint for ephemeral visual QA.
# Critical: this process must NEVER exit while the QA pipeline needs captures.
# The snap player often crashes under Docker/Xvfb; we keep Xvfb (+ optional
# fallback renderer) alive regardless.
set -uo pipefail

# Software GL under Xvfb. Snap libGL can only load the snap's own swrast_dri
# (host Mesa DRI fails with undefined amdgpu symbols against snap libGL).
# Never point LIBGL_DRIVERS_PATH at host /usr/lib/.../dri.
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export GALLIUM_DRIVER="${GALLIUM_DRIVER:-llvmpipe}"

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
# ZeroMQ publish address players use to receive push messages (compose-network hostname).
XMR_ADDRESS="${XIBO_XMR_ADDRESS:-tcp://cms-xmr:9505}"
PLAYER_CONFIG_DIR="${PLAYER_CONFIG_DIR:-/var/lib/xibo-player}"
# Prefer a native container volume for the media library. Docker Desktop bind mounts
# of empty Windows dirs often fail the player's FileSystem::exists() check.
PLAYER_LIBRARY_DIR="${XIBO_LOCAL_LIBRARY:-${PLAYER_CONFIG_DIR}/library}"
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
export SNAP_VERSION="${SNAP_VERSION:-1.8-R6}"
export SNAP_REVISION="${SNAP_REVISION:-6}"
export HOME="${HOME:-/root}"

# WebKitGTK under Xvfb: disable compositing to avoid HTML-package paint crashes.
export WEBKIT_DISABLE_COMPOSITING_MODE="${WEBKIT_DISABLE_COMPOSITING_MODE:-1}"
export WEBKIT_FORCE_COMPOSITING_MODE="${WEBKIT_FORCE_COMPOSITING_MODE:-0}"
export WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"

mkdir -p "${ARTIFACTS_DIR}" "${PLAYER_CONFIG_DIR}" "${PLAYER_LIBRARY_DIR}" \
  "${HOME}/snap/xibo-player/common"

if [[ -f "${PLAYER_CONFIG_DIR}/snap-common/cmsSettings.xml" ]]; then
  cp -f "${PLAYER_CONFIG_DIR}/snap-common/cmsSettings.xml" \
    "${HOME}/snap/xibo-player/common/cmsSettings.xml"
fi

log() {
  printf '[entrypoint] %s\n' "$*"
}

normalize_xml_file() {
  # Strip CR from Windows bind-mounted configs (breaks path values / XML parsing).
  local path="$1"
  if [[ -f "${path}" ]]; then
    sed -i 's/\r$//' "${path}" 2>/dev/null || true
  fi
}

write_player_config() {
  local cms_xml="${SNAP_USER_COMMON}/cmsSettings.xml"
  local home_xml="${HOME}/snap/xibo-player/common/cmsSettings.xml"
  local player_xml="${SNAP_USER_COMMON}/playerSettings.xml"

  mkdir -p "${PLAYER_LIBRARY_DIR}"
  # Ensure the directory is non-empty so bind-mount edge cases still materialize.
  touch "${PLAYER_LIBRARY_DIR}/.keep"

  # Pipeline-provisioned bind mount is the source of truth. Docker Compose on
  # WSL/Windows often interpolates a stale/empty XIBO_CMS_KEY even when
  # compose.runtime.env has the live SERVER_KEY — never clobber a good file.
  local existing_key=""
  if [[ -f "${cms_xml}" ]]; then
    existing_key="$(sed -n 's/.*<key>\([^<]*\)<\/key>.*/\1/p' "${cms_xml}" | head -n1)"
  fi
  if [[ -n "${existing_key}" ]]; then
    CMS_KEY="${existing_key}"
    normalize_xml_file "${cms_xml}"
    mkdir -p "$(dirname "${home_xml}")"
    cp -f "${cms_xml}" "${home_xml}"
    normalize_xml_file "${home_xml}"
    log "Using provisioned cmsSettings.xml (key_len=${#CMS_KEY}); not overwriting from env"
  else
    if [[ -z "${CMS_KEY}" ]]; then
      log "WARNING: no provisioned cmsSettings key and XIBO_CMS_KEY empty — RegisterDisplay will fail"
    fi
    cat >"${cms_xml}" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<settings version="2">
  <cmsAddress>${CMS_URL}</cmsAddress>
  <key>${CMS_KEY}</key>
  <localLibrary>${PLAYER_LIBRARY_DIR}</localLibrary>
  <displayId>${HARDWARE_KEY}</displayId>
</settings>
EOF
    mkdir -p "$(dirname "${home_xml}")"
    cp -f "${cms_xml}" "${home_xml}"
    normalize_xml_file "${cms_xml}"
    normalize_xml_file "${home_xml}"
    log "Wrote cmsSettings.xml from env (key_len=${#CMS_KEY})"
  fi

  # Always refresh playerSettings (non-secret) for QA collectInterval / XMR address.
  cat >"${player_xml}" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<settings version="2">
  <displayName>${DISPLAY_NAME}</displayName>
  <sizeX>1920</sizeX>
  <sizeY>1080</sizeY>
  <offsetX>0</offsetX>
  <offsetY>0</offsetY>
  <offfsetY>0</offfsetY>
  <preventSleep>true</preventSleep>
  <collectInterval>30</collectInterval>
  <logLevel>debug</logLevel>
  <xmrNetworkAddress>${XMR_ADDRESS}</xmrNetworkAddress>
</settings>
EOF
  normalize_xml_file "${player_xml}"

  cat >"${PLAYER_CONFIG_DIR}/config.json" <<EOF
{
  "cmsAddress": "${CMS_URL}",
  "cmsKey": "${CMS_KEY}",
  "displayName": "${DISPLAY_NAME}",
  "displayId": "${HARDWARE_KEY}",
  "localLibrary": "${PLAYER_LIBRARY_DIR}",
  "xmrNetworkAddress": "${XMR_ADDRESS}"
}
EOF
  log "Player config ready library=${PLAYER_LIBRARY_DIR} xmr=${XMR_ADDRESS} key_len=${#CMS_KEY}"
  if [[ ! -d "${PLAYER_LIBRARY_DIR}" ]]; then
    log "ERROR: localLibrary directory missing: ${PLAYER_LIBRARY_DIR}"
  else
    log "localLibrary ok: $(ls -ld "${PLAYER_LIBRARY_DIR}")"
  fi
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
# +extension GLX is required for Gtk/OpenGL paint (RegionImpl::start).
# Do not bind-mount snap DRI over host DRI — that breaks Xvfb's GLX module.
Xvfb "${DISPLAY}" -screen 0 "${SCREEN_GEOMETRY}" -ac -nolisten tcp \
  +extension GLX +render -noreset \
  >"${XVFB_LOG}" 2>&1 &
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

write_player_config

export GST_PLUGIN_PATH="${SNAP}/usr/lib/gstreamer-1.0${GST_PLUGIN_PATH:+:$GST_PLUGIN_PATH}"
export GST_PLUGIN_SYSTEM_PATH="${SNAP}/usr/lib/gstreamer-1.0"
export GST_PLUGIN_SCANNER="${SNAP}/usr/libexec/gstreamer-1.0/gst-plugin-scanner"
# Snap runtime libs first (GTK/GLib ABI). Player Mesa must load snap swrast via
# LIBGL_DRIVERS_PATH. Never bind-mount snap DRI over host — Xvfb needs host Mesa GLX.
export LD_LIBRARY_PATH="${SNAP}/usr/lib:${SNAP}/lib:${SNAP}/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
SNAP_DRI="${SNAP}/usr/lib/x86_64-linux-gnu/dri"
if [[ -d "${SNAP_DRI}" ]]; then
  export LIBGL_DRIVERS_PATH="${SNAP_DRI}"
else
  log "WARNING: snap DRI missing at ${SNAP_DRI}"
fi
# Help Mesa find LLVM/tinfo deps shipped beside snap libs.
if [[ -d "${SNAP}/usr/lib/llvm-10/lib" ]]; then
  export LD_LIBRARY_PATH="${SNAP}/usr/lib/llvm-10/lib:${LD_LIBRARY_PATH}"
fi
export PATH="${SNAP}/bin:${PATH}"
log "GL: ALWAYS_SOFTWARE=${LIBGL_ALWAYS_SOFTWARE} DRIVER=${GALLIUM_DRIVER} DRIVERS=${LIBGL_DRIVERS_PATH:-unset}"
log "WebKit: DISABLE_COMPOSITING=${WEBKIT_DISABLE_COMPOSITING_MODE} FORCE_COMPOSITING=${WEBKIT_FORCE_COMPOSITING_MODE}"

# One-shot swrast probe (non-fatal) so rebuild logs show whether Mesa can load.
if command -v glxinfo >/dev/null 2>&1; then
  : >"${ARTIFACTS_DIR}/glxinfo.log"
  if LIBGL_DEBUG=verbose glxinfo -B >>"${ARTIFACTS_DIR}/glxinfo.log" 2>&1; then
    log "glxinfo OK (see ${ARTIFACTS_DIR}/glxinfo.log)"
  else
    log "glxinfo failed (see ${ARTIFACTS_DIR}/glxinfo.log); continuing"
  fi
  if ! xdpyinfo -display "${DISPLAY}" -queryExtensions 2>/dev/null | grep -qi 'GLX'; then
    log "WARNING: X server has no GLX extension — RegionImpl paint will likely SIGSEGV"
  fi
fi
# Prefer snap GIO modules — host Ubuntu modules crash against the snap's older GLib/GnuTLS.
if [[ -d "${SNAP}/usr/lib/x86_64-linux-gnu/gio/modules" ]]; then
  export GIO_MODULE_DIR="${SNAP}/usr/lib/x86_64-linux-gnu/gio/modules"
fi
if [[ -f /etc/xibo-qa/gdk-pixbuf-loaders.cache ]]; then
  export GDK_PIXBUF_MODULE_FILE=/etc/xibo-qa/gdk-pixbuf-loaders.cache
fi
# Host /etc/fonts on Ubuntu 22.04 uses XML attrs the snap's older fontconfig rejects.
if [[ -f "${SNAP}/etc/fonts/fonts.conf" ]]; then
  export FONTCONFIG_PATH="${SNAP}/etc/fonts"
  export FONTCONFIG_FILE="${SNAP}/etc/fonts/fonts.conf"
fi
# Promote <settings> XML + empty localLibrary fallback (see player_qa_shim.cpp).
if [[ -f /usr/local/lib/libxibo_qa_shim.so ]]; then
  export LD_PRELOAD="/usr/local/lib/libxibo_qa_shim.so${LD_PRELOAD:+:$LD_PRELOAD}"
  export XIBO_LOCAL_LIBRARY="${PLAYER_LIBRARY_DIR}"
  export XIBO_CMS_CONNECT_HOST="${XIBO_CMS_CONNECT_HOST:-cms-web}"
  log "LD_PRELOAD qa shim enabled (library=${XIBO_LOCAL_LIBRARY})"
fi

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

# Default: Xibo Linux Player only. Chromium/feh preview is opt-in for debugging.
USE_TIMELINE_PREVIEW="${QA_USE_TIMELINE_PREVIEW:-0}"
if [[ "${USE_TIMELINE_PREVIEW}" == "1" || "${USE_TIMELINE_PREVIEW}" == "true" ]]; then
  log "QA_USE_TIMELINE_PREVIEW enabled; starting Chromium/feh fallback renderer"
  start_fallback_renderer
else
  log "Xibo player mode (set QA_USE_TIMELINE_PREVIEW=1 for Chromium timeline preview)"
fi

player_supervisor() {
  local attempts=0
  local backoff=2
  if [[ ! -x "${PLAYER_BIN}" ]]; then
    log "Xibo player binary missing (${PLAYER_BIN}); Xvfb remains up for diagnostics"
    return
  fi
  # Keep restarting while the container is up so a fixed GL/env can recover mid-run
  # before capture. Do not permanently give up (black Xvfb-only captures).
  while [[ "${RUNNING}" -eq 1 ]]; do
    attempts=$((attempts + 1))
    log "Launching Xibo Linux Player attempt=${attempts} backoff=${backoff}s"
    if [[ -x "${SNAP_RUN}" && -x "${PLAYER_BIN}" ]]; then
      # Prefer the player binary directly; watchdog exit was crash-looping the container.
      "${SNAP_RUN}" "${PLAYER_BIN}" >>"${PLAYER_LOG}" 2>&1 &
    else
      "${PLAYER_BIN}" >>"${PLAYER_LOG}" 2>&1 &
    fi
    local pid=$!
    wait "${pid}" || true
    log "Player exited; see ${PLAYER_LOG}"
    sleep "${backoff}"
    if [[ "${backoff}" -lt 15 ]]; then
      backoff=$((backoff + 1))
    fi
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
