#!/usr/bin/env bash
# Install official Xibo CMS via Docker under /opt/xibo.
# Prefer running after bootstrap-cms-host.sh. Requires root for /opt/xibo.
set -euo pipefail

XIBO_ROOT="${XIBO_ROOT:-/opt/xibo}"
XIBO_DOWNLOAD_URL="${XIBO_DOWNLOAD_URL:-https://xibosignage.com/api/downloads/cms}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found. Run bootstrap-cms-host.sh first." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin not found. Install docker-compose-v2." >&2
  exit 1
fi

mkdir -p "${XIBO_ROOT}"
cd "${XIBO_ROOT}"

if [[ -f docker-compose.yml || -f compose.yaml ]]; then
  echo "Existing compose file in ${XIBO_ROOT}."
  echo "Refusing to overwrite. To reinstall, move/backup this directory first." >&2
  exit 1
fi

TMP_ARCHIVE="$(mktemp /tmp/xibo-docker.XXXXXX.tar.gz)"
cleanup() { rm -f "${TMP_ARCHIVE}"; }
trap cleanup EXIT

echo "==> Downloading Xibo Docker bundle"
curl -fsSL -o "${TMP_ARCHIVE}" "${XIBO_DOWNLOAD_URL}"

echo "==> Extracting into ${XIBO_ROOT}"
tar --strip-components=1 -xzf "${TMP_ARCHIVE}" -C "${XIBO_ROOT}"

if [[ ! -f config.env.template ]]; then
  echo "config.env.template missing after extract; archive layout unexpected." >&2
  exit 1
fi

if [[ ! -f config.env ]]; then
  MYSQL_PASSWORD="$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 16 || true)"
  if [[ ${#MYSQL_PASSWORD} -ne 16 ]]; then
    echo "Failed to generate MYSQL_PASSWORD." >&2
    exit 1
  fi
  cp config.env.template config.env
  # Replace empty / placeholder MYSQL_PASSWORD= lines in the template.
  if grep -q '^MYSQL_PASSWORD=' config.env; then
    sed -i "s/^MYSQL_PASSWORD=.*/MYSQL_PASSWORD=${MYSQL_PASSWORD}/" config.env
  else
    printf '\nMYSQL_PASSWORD=%s\n' "${MYSQL_PASSWORD}" >> config.env
  fi
  chmod 600 config.env
  echo "Wrote ${XIBO_ROOT}/config.env (MYSQL_PASSWORD auto-generated)."
  echo "Store this password with facility secrets; needed for upgrades."
else
  echo "Using existing ${XIBO_ROOT}/config.env"
fi

echo "==> Starting Xibo stack (first boot may take several minutes)"
docker compose up -d

echo
echo "Xibo CMS containers are starting."
echo "  UI:      http://$(hostname -I | awk '{print $1}')/"
echo "  Default: xibo_admin / password  — change immediately"
echo "  Data:    ${XIBO_ROOT}/shared/"
echo "  Config:  ${XIBO_ROOT}/config.env"
echo
echo "Then follow ops/runbooks/install-cms-host.md section 6 (folders, CMS key, API)."
