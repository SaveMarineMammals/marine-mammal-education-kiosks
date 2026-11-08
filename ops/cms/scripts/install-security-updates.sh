#!/usr/bin/env bash
# Configure unattended security updates (01:00-05:00 reboot window), install
# admin-alert + CMS stack-update units, and optionally write /etc/mmek/alert.env.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
UNIT_DIR="${REPO_ROOT}/ops/cms/systemd"
ALERT_ENV="${MMEK_ALERT_ENV:-/etc/mmek/alert.env}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

export DEBIAN_FRONTEND=noninteractive

log() { echo "==> $*"; }

log "Installing packages"
apt-get update -y
apt-get install -y unattended-upgrades apt-listchanges curl ca-certificates python3

log "Timezone America/Belize (facility default)"
timedatectl set-timezone America/Belize || true

log "unattended-upgrades: security + reboot at 02:00 local"
cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
EOF

cat >/etc/apt/apt.conf.d/52unattended-reboot-mmek <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "02:00";
Unattended-Upgrade::Automatic-Reboot-WithUsers "true";
EOF

# Prefer Ubuntu security pocket when origins file exists; otherwise defaults.
if [[ -f /etc/apt/apt.conf.d/50unattended-upgrades ]]; then
  dpkg-reconfigure -f noninteractive unattended-upgrades || true
fi

log "Installing mmek-admin-alert and cms-stack-update"
install -d -m 0755 /usr/local/sbin /etc/mmek /var/lib/mmek
install -m 0755 "${SCRIPT_DIR}/mmek-admin-alert.sh" /usr/local/sbin/mmek-admin-alert
install -m 0755 "${SCRIPT_DIR}/cms-stack-update.sh" /usr/local/sbin/cms-stack-update

install -m 0644 "${UNIT_DIR}/mmek-cms-stack-update.service" /etc/systemd/system/mmek-cms-stack-update.service
install -m 0644 "${UNIT_DIR}/mmek-cms-stack-update.timer" /etc/systemd/system/mmek-cms-stack-update.timer
install -m 0644 "${UNIT_DIR}/mmek-admin-alert@.service" /etc/systemd/system/mmek-admin-alert@.service

if [[ ! -f "${ALERT_ENV}" ]]; then
  if [[ -f "${REPO_ROOT}/ops/cms/alert.env.example" ]]; then
    install -m 0600 "${REPO_ROOT}/ops/cms/alert.env.example" "${ALERT_ENV}"
    log "Wrote ${ALERT_ENV} from example — fill ALERT_LAMBDA_URL and ALERT_INGEST_TOKEN"
  fi
fi

# Ensure alert role is cms on this host
if [[ -f "${ALERT_ENV}" ]] && ! grep -q '^ALERT_ROLE=' "${ALERT_ENV}"; then
  printf '\nALERT_ROLE=cms\n' >> "${ALERT_ENV}"
fi

systemctl daemon-reload
systemctl enable --now mmek-cms-stack-update.timer
systemctl enable unattended-upgrades.service || true

log "Done. Timer:"
systemctl list-timers mmek-cms-stack-update.timer --no-pager || true
echo
echo "Next:"
echo "  1. Complete Sent.dm + Terraform admin-alert (ops/runbooks/sent-dm-alerts.md)"
echo "  2. Set ALERT_LAMBDA_URL / ALERT_INGEST_TOKEN in ${ALERT_ENV}"
echo "  3. Test: MMEK_FORCE_UPDATE=1 /usr/local/sbin/cms-stack-update"
echo "  4. Test alert: /usr/local/sbin/mmek-admin-alert test_alert 'manual smoke'"
