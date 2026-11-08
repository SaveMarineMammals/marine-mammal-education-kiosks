#!/usr/bin/env bash
# Off-hours Xibo Docker stack refresh + smoke. Called by mmek-cms-stack-update.service.
# On permanent failure (2 consecutive hard fails), invoke mmek-admin-alert.
set -euo pipefail

XIBO_ROOT="${XIBO_ROOT:-/opt/xibo}"
STATE_DIR="${MMEK_UPDATE_STATE_DIR:-/var/lib/mmek}"
FAIL_FILE="${STATE_DIR}/cms-stack-update-failures"
ALERT_BIN="${MMEK_ADMIN_ALERT:-/usr/local/sbin/mmek-admin-alert}"
CMS_HOST="${CMS_HOSTNAME:-server.kiosks.local.belize.savemarinemammals.com}"
MAX_FAILS="${MMEK_STACK_UPDATE_MAX_FAILS:-2}"

log() { echo "==> $*"; }
die() { echo "error: $*" >&2; exit 1; }

install -d -m 0755 "${STATE_DIR}"

HOUR="$(date +%H)"
# Allow forced runs (MMEK_FORCE_UPDATE=1) outside the window for testing.
if [[ "${MMEK_FORCE_UPDATE:-0}" != "1" ]]; then
  if [[ "${HOUR}" -lt 1 || "${HOUR}" -ge 5 ]]; then
    log "outside 01:00-05:00 local window (hour=${HOUR}); skipping"
    exit 0
  fi
fi

[[ -d "${XIBO_ROOT}" ]] || die "missing ${XIBO_ROOT}"
cd "${XIBO_ROOT}"
[[ -f docker-compose.yml || -f compose.yaml ]] || die "no compose file in ${XIBO_ROOT}"

record_failure() {
  local n=0
  if [[ -f "${FAIL_FILE}" ]]; then
    n="$(tr -dc '0-9' < "${FAIL_FILE}" || true)"
    n="${n:-0}"
  fi
  n=$((n + 1))
  echo "${n}" > "${FAIL_FILE}"
  echo "cms-stack-update: failure count=${n}" >&2
  if [[ "${n}" -ge "${MAX_FAILS}" ]]; then
    if [[ -x "${ALERT_BIN}" ]]; then
      "${ALERT_BIN}" "cms_stack_update_failed" "consecutive failures=${n} at ${XIBO_ROOT}" || true
    else
      echo "warning: alert helper missing at ${ALERT_BIN}" >&2
    fi
  fi
}

clear_failures() {
  rm -f "${FAIL_FILE}"
  rm -f "${STATE_DIR}/alert-sent/cms_stack_update_failed" 2>/dev/null || true
}

smoke() {
  docker compose ps --status running >/dev/null
  curl -fsS --max-time 20 "https://${CMS_HOST}/login" -o /dev/null
  # XMR typically published on host :9505
  if command -v ss >/dev/null 2>&1; then
    ss -ltn | grep -q ':9505' || die "XMR port 9505 not listening"
  fi
}

if ! {
  log "docker compose pull"
  docker compose pull
  log "docker compose up -d"
  # TLS loopback bind is already rewritten into compose by enable-cms-tls.sh.
  docker compose up -d
  sleep 5
  log "smoke checks"
  smoke
}; then
  record_failure
  exit 1
fi

clear_failures
log "stack update ok"
