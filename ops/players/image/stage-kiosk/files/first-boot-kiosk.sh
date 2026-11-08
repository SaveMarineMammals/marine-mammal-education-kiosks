#!/bin/bash
# Apply /boot/firmware/kiosk.conf once, then mark first-boot complete.
set -euo pipefail

CONF="/boot/firmware/kiosk.conf"
# Older boot layout fallback
if [[ ! -f "${CONF}" && -f /boot/kiosk.conf ]]; then
  CONF="/boot/kiosk.conf"
fi

MARKER_DIR="/var/lib/mmek"
MARKER="${MARKER_DIR}/first-boot-complete"
ENV_FILE="/etc/mmek/arexibo.env"

if [[ -f "${MARKER}" ]]; then
  exit 0
fi

if [[ ! -f "${CONF}" ]]; then
  echo "first-boot-kiosk: missing ${CONF}; skipping" >&2
  exit 0
fi

# Windows/WSL copies often leave CRLF; strip before parse.
sed -i 's/\n$//' "${CONF}" || true

# shellcheck disable=SC1090
set -a
# Parse KEY=VALUE lines (ignore comments/blank)
while IFS= read -r line || [[ -n "${line}" ]]; do
  line="${line%$'\n'}"
  [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]] && continue
  if [[ "${line}" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
    export "${BASH_REMATCH[1]}=${BASH_REMATCH[2]}"
  fi
done < "${CONF}"
set +a

: "${HOSTNAME:?HOSTNAME required in kiosk.conf}"
: "${CMS_URL:?CMS_URL required in kiosk.conf}"
: "${CMS_KEY:?CMS_KEY required in kiosk.conf}"
: "${TS_AUTHKEY:?TS_AUTHKEY required in kiosk.conf (tag:mmek-players Tailscale auth key)}"

if command -v hostnamectl >/dev/null 2>&1; then
  hostnamectl set-hostname "${HOSTNAME}"
else
  echo "${HOSTNAME}" >/etc/hostname
  hostname "${HOSTNAME}" || true
fi
if grep -qE '^10\.0\.0\.1|^127\.0\.1\.1' /etc/hosts; then
  sed -i -E "s/^(10\.0\.0\.1|127\.0\.1\.1)[[:space:]].*/\\1\\t${HOSTNAME}/" /etc/hosts
else
  echo -e "127.0.1.1\t${HOSTNAME}" >> /etc/hosts
fi

# Join facility Tailscale before Arexibo (CMS_URL resolves via split DNS on the tailnet).
if ! command -v tailscale >/dev/null 2>&1; then
  echo "first-boot-kiosk: tailscale not installed in image" >&2
  exit 1
fi
systemctl enable --now tailscaled
tailscale up \
  --hostname="${HOSTNAME}" \
  --advertise-tags=tag:mmek-players \
  --auth-key="${TS_AUTHKEY}" \
  --accept-dns=true

echo "first-boot-kiosk: waiting for Tailscale IP..."
TS_READY=0
for _ in $(seq 1 60); do
  if TS_IP="$(tailscale ip -4 2>/dev/null)" && [[ -n "${TS_IP}" ]]; then
    echo "first-boot-kiosk: Tailscale ipv4=${TS_IP}"
    TS_READY=1
    break
  fi
  sleep 2
done
if [[ "${TS_READY}" -ne 1 ]]; then
  echo "first-boot-kiosk: Tailscale did not come up in time; check auth key / ACL tags" >&2
  exit 1
fi

install -d -m 0750 /etc/mmek
umask 077
cat > "${ENV_FILE}" <<EOF
CMS_URL=${CMS_URL}
CMS_KEY=${CMS_KEY}
EOF
chmod 0600 "${ENV_FILE}"
chown root:root "${ENV_FILE}"

# Optional admin-alert Lambda credentials (never bake into golden image).
ALERT_ENV="/etc/mmek/alert.env"
if [[ -n "${ALERT_LAMBDA_URL:-}" && -n "${ALERT_INGEST_TOKEN:-}" ]]; then
  cat > "${ALERT_ENV}" <<EOF
ALERT_LAMBDA_URL=${ALERT_LAMBDA_URL}
ALERT_INGEST_TOKEN=${ALERT_INGEST_TOKEN}
ALERT_ROLE=player
ALERT_HOSTNAME=${HOSTNAME}
EOF
  chmod 0600 "${ALERT_ENV}"
  chown root:root "${ALERT_ENV}"
fi

install -d -m 0755 /var/lib/arexibo
chown -R kiosk:kiosk /var/lib/arexibo
# Keep kiosk home writable for Mesa/Qt caches (X may start as root).
install -d -m 0755 /home/kiosk/.cache
chown -R kiosk:kiosk /home/kiosk

systemctl enable mmek-kiosk-display.service arexibo.service mmek-post-update-health.service || true
# First boot already has a running multi-user target — start now, do not wait for reboot.
systemctl start mmek-kiosk-display.service || true
systemctl start arexibo.service || true
systemctl start mmek-post-update-health.service || true

install -d -m 0755 "${MARKER_DIR}"
{
  echo "hostname=${HOSTNAME}"
  echo "cms_url=${CMS_URL}"
  echo "display_group=${DISPLAY_GROUP:-}"
  echo "tailscale_ipv4=$(tailscale ip -4 2>/dev/null || true)"
  echo "alert_configured=$([[ -f ${ALERT_ENV} ]] && echo yes || echo no)"
  echo "completed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "${MARKER}"
chmod 0644 "${MARKER}"

# Remove secrets from the boot partition after copying to root-only env.
# Keep a non-secret stub so operators know first-boot already ran.
cat > "${CONF}" <<EOF
# Consumed by first-boot-kiosk on $(date -u +%Y-%m-%dT%H:%M:%SZ).
# Secrets removed from bootfs; active config is ${ENV_FILE}; Tailscale via tailscaled.
HOSTNAME=${HOSTNAME}
CMS_URL=${CMS_URL}
DISPLAY_GROUP=${DISPLAY_GROUP:-}
# CMS_KEY=removed-after-first-boot
# TS_AUTHKEY=removed-after-first-boot
# ALERT_INGEST_TOKEN=removed-after-first-boot
EOF

echo "first-boot-kiosk: configured ${HOSTNAME}"
