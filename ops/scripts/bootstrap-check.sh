#!/usr/bin/env bash
# SSH smoke test against a provisioned kiosk Pi.
# Usage: bootstrap-check.sh <hostname-or-ip> [ssh-user]
set -euo pipefail

TARGET="${1:-}"
USER_NAME="${2:-mmek}"

if [[ -z "${TARGET}" ]]; then
  echo "usage: $0 <hostname-or-ip> [ssh-user]" >&2
  exit 2
fi

SSH=(ssh -o BatchMode=yes -o ConnectTimeout=10 "${USER_NAME}@${TARGET}")

echo "==> host: ${USER_NAME}@${TARGET}"

REMOTE_HOST="$("${SSH[@]}" hostname)"
echo "hostname: ${REMOTE_HOST}"
if [[ ! "${REMOTE_HOST}" =~ ^kiosk-[a-z0-9]+(-[a-z0-9]+)*-[0-9]{2,3}$ ]]; then
  echo "warning: hostname does not match kiosk-<location>-<nn>" >&2
fi

echo "==> arexibo.service"
"${SSH[@]}" systemctl is-active arexibo.service

echo "==> mmek-kiosk-display.service"
"${SSH[@]}" systemctl is-active mmek-kiosk-display.service

echo "==> CMS_URL present (value not printed)"
"${SSH[@]}" bash -c 'test -f /etc/mmek/arexibo.env && grep -q "^CMS_URL=." /etc/mmek/arexibo.env'

echo "==> first-boot marker"
"${SSH[@]}" test -f /var/lib/mmek/first-boot-complete

echo "ok"
