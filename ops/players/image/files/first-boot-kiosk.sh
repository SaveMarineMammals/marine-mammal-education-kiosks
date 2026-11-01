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

# shellcheck disable=SC1090
set -a
# Parse KEY=VALUE lines (ignore comments/blank)
while IFS= read -r line || [[ -n "${line}" ]]; do
  [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]] && continue
  if [[ "${line}" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
    export "${BASH_REMATCH[1]}=${BASH_REMATCH[2]}"
  fi
done < "${CONF}"
set +a

: "${HOSTNAME:?HOSTNAME required in kiosk.conf}"
: "${CMS_URL:?CMS_URL required in kiosk.conf}"
: "${CMS_KEY:?CMS_KEY required in kiosk.conf}"

hostnamectl set-hostname "${HOSTNAME}"
if grep -qE '^10\.0\.0\.1|^127\.0\.1\.1' /etc/hosts; then
  sed -i -E "s/^(10\.0\.0\.1|127\.0\.1\.1)[[:space:]].*/\\1\\t${HOSTNAME}/" /etc/hosts
else
  echo -e "127.0.1.1\t${HOSTNAME}" >> /etc/hosts
fi

install -d -m 0750 /etc/mmek
umask 077
cat > "${ENV_FILE}" <<EOF
CMS_URL=${CMS_URL}
CMS_KEY=${CMS_KEY}
EOF
chmod 0600 "${ENV_FILE}"
chown root:root "${ENV_FILE}"

install -d -m 0755 /var/lib/arexibo
chown -R kiosk:kiosk /var/lib/arexibo

systemctl enable mmek-kiosk-display.service arexibo.service || true

install -d -m 0755 "${MARKER_DIR}"
{
  echo "hostname=${HOSTNAME}"
  echo "cms_url=${CMS_URL}"
  echo "display_group=${DISPLAY_GROUP:-}"
  echo "completed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "${MARKER}"
chmod 0644 "${MARKER}"

# Remove secrets from the boot partition after copying to root-only env.
# Keep a non-secret stub so operators know first-boot already ran.
cat > "${CONF}" <<EOF
# Consumed by first-boot-kiosk on $(date -u +%Y-%m-%dT%H:%M:%SZ).
# Secrets removed from bootfs; active config is ${ENV_FILE}.
HOSTNAME=${HOSTNAME}
CMS_URL=${CMS_URL}
DISPLAY_GROUP=${DISPLAY_GROUP:-}
# CMS_KEY=removed-after-first-boot
EOF

echo "first-boot-kiosk: configured ${HOSTNAME}"
