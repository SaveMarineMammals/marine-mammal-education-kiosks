#!/usr/bin/env bash
# Post-boot health for kiosk players. Alerts on permanent failure after upgrades.
set -euo pipefail

ALERT_BIN="${MMEK_ADMIN_ALERT:-/usr/local/sbin/mmek-admin-alert}"
STATE_DIR="/var/lib/mmek"
FAIL_FILE="${STATE_DIR}/post-update-health-failures"
MAX_FAILS="${MMEK_HEALTH_MAX_FAILS:-1}"

install -d -m 0755 "${STATE_DIR}"

fail() {
  local msg="$1"
  echo "mmek-post-update-health: ${msg}" >&2
  local n=0
  if [[ -f "${FAIL_FILE}" ]]; then
    n="$(tr -dc '0-9' < "${FAIL_FILE}" || true)"
    n="${n:-0}"
  fi
  n=$((n + 1))
  echo "${n}" > "${FAIL_FILE}"
  if [[ "${n}" -ge "${MAX_FAILS}" && -x "${ALERT_BIN}" ]]; then
    ALERT_ROLE=player "${ALERT_BIN}" "player_health_failed" "${msg}" || true
  fi
  exit 1
}

# Wait briefly for display stack after boot.
sleep 15

systemctl is-active --quiet mmek-kiosk-display.service || fail "mmek-kiosk-display inactive"
systemctl is-active --quiet arexibo.service || fail "arexibo inactive"

if [[ -f /etc/mmek/arexibo.env ]]; then
  # shellcheck disable=SC1091
  set -a
  # shellcheck disable=SC1091
  source /etc/mmek/arexibo.env
  set +a
  if [[ -n "${CMS_URL:-}" ]]; then
    curl -fsS --max-time 20 "${CMS_URL%/}/login" -o /dev/null || fail "CMS unreachable at ${CMS_URL}"
  fi
fi

rm -f "${FAIL_FILE}"
rm -f "${STATE_DIR}/alert-sent/player_health_failed" 2>/dev/null || true
echo "mmek-post-update-health: ok"
