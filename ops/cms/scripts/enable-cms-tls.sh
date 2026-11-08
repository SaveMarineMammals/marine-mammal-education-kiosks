#!/usr/bin/env bash
# Terminate TLS for Xibo CMS with Caddy + Let's Encrypt DNS-01 (Route 53).
# Run on the CMS host after install-xibo-cms.sh.
# Requires /etc/mmek/caddy-acme.env (AWS keys) — see ops/cms/caddy/caddy-acme.env.example.
# Idempotent: safe to re-run after Xibo upgrades that restore public :80.
set -euo pipefail

XIBO_ROOT="${XIBO_ROOT:-/opt/xibo}"
CMS_HOSTNAME="${CMS_HOSTNAME:-server.kiosks.local.belize.savemarinemammals.com}"
CMS_LOOPBACK_PORT="${CMS_LOOPBACK_PORT:-8080}"
ACME_ENV_FILE="${ACME_ENV_FILE:-/etc/mmek/caddy-acme.env}"
GO_VERSION="${GO_VERSION:-1.24.2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_CADDYFILE="${SCRIPT_DIR}/../caddy/Caddyfile"
REPO_ACME_ENV_EXAMPLE="${SCRIPT_DIR}/../caddy/caddy-acme.env.example"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

export DEBIAN_FRONTEND=noninteractive

if [[ ! -d "${XIBO_ROOT}" ]]; then
  echo "Xibo root ${XIBO_ROOT} not found. Run install-xibo-cms.sh first." >&2
  exit 1
fi

COMPOSE_FILE=""
for candidate in "${XIBO_ROOT}/docker-compose.yml" "${XIBO_ROOT}/compose.yaml"; do
  if [[ -f "${candidate}" ]]; then
    COMPOSE_FILE="${candidate}"
    break
  fi
done
if [[ -z "${COMPOSE_FILE}" ]]; then
  echo "No docker-compose.yml / compose.yaml under ${XIBO_ROOT}." >&2
  exit 1
fi

if [[ ! -f "${REPO_CADDYFILE}" ]]; then
  echo "Missing Caddyfile template at ${REPO_CADDYFILE}." >&2
  exit 1
fi

require_acme_env() {
  if [[ ! -f "${ACME_ENV_FILE}" ]]; then
    echo "Missing ${ACME_ENV_FILE}." >&2
    echo "Create it from ${REPO_ACME_ENV_EXAMPLE} with Route 53 IAM access keys." >&2
    echo "  sudo mkdir -p /etc/mmek" >&2
    echo "  sudo cp ${REPO_ACME_ENV_EXAMPLE} ${ACME_ENV_FILE}" >&2
    echo "  sudo chmod 600 ${ACME_ENV_FILE}" >&2
    echo "  sudo nano ${ACME_ENV_FILE}" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  set -a
  # shellcheck source=/dev/null
  source "${ACME_ENV_FILE}"
  set +a
  if [[ -z "${AWS_ACCESS_KEY_ID:-}" || -z "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
    echo "${ACME_ENV_FILE} must set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY." >&2
    exit 1
  fi
  if [[ -z "${AWS_HOSTED_ZONE_ID:-}" ]]; then
    echo "${ACME_ENV_FILE} must set AWS_HOSTED_ZONE_ID to the kiosks.local zone (terraform output kiosks_zone_id)." >&2
    exit 1
  fi
  : "${AWS_REGION:=us-east-1}"
  echo "Using ACME DNS-01 credentials from ${ACME_ENV_FILE} (region ${AWS_REGION}, zone ${AWS_HOSTED_ZONE_ID})"
}

bind_cms_web_loopback() {
  local compose="$1"
  local backup="${compose}.pre-tls.bak"
  # Prefer exact loopback check first — substring "80:80" also appears inside "8080:80".
  if grep -qE "127\\.0\\.0\\.1:${CMS_LOOPBACK_PORT}:80" "${compose}"; then
    echo "cms-web already bound to 127.0.0.1:${CMS_LOOPBACK_PORT}."
    return 0
  fi
  if ! grep -qE '"80:80"' "${compose}" \
    && ! grep -qE '(^|[[:space:]])80:80([[:space:]]|$)' "${compose}"; then
    echo "Could not find a host :80 publish in ${compose}; check cms-web ports manually." >&2
    exit 1
  fi
  if [[ ! -f "${backup}" ]]; then
    cp -a "${compose}" "${backup}"
    echo "Backed up compose to ${backup}"
  fi
  # Official Xibo bundle publishes cms-web as "80:80" (quoted or bare).
  sed -i -E \
    -e "s/\"80:80\"/\"127.0.0.1:${CMS_LOOPBACK_PORT}:80\"/g" \
    -e "s/(^|[[:space:]])80:80([[:space:]]|$)/\\1127.0.0.1:${CMS_LOOPBACK_PORT}:80\\2/g" \
    "${compose}"
  if ! grep -qE "127\\.0\\.0\\.1:${CMS_LOOPBACK_PORT}:80" "${compose}"; then
    echo "Failed to rewrite cms-web ports in ${compose}." >&2
    exit 1
  fi
  if grep -qE '"80:80"' "${compose}" \
    || grep -qE '(^|[[:space:]])80:80([[:space:]]|$)' "${compose}"; then
    echo "Warning: ${compose} still has a public 80:80 mapping; inspect before continuing." >&2
  fi
  echo "Bound cms-web to 127.0.0.1:${CMS_LOOPBACK_PORT}:80 in ${compose}"
}

set_cms_server_name() {
  local env_file="${XIBO_ROOT}/config.env"
  if [[ ! -f "${env_file}" ]]; then
    echo "Missing ${env_file}; run install-xibo-cms.sh first." >&2
    exit 1
  fi
  if grep -q '^CMS_SERVER_NAME=' "${env_file}"; then
    sed -i "s/^CMS_SERVER_NAME=.*/CMS_SERVER_NAME=${CMS_HOSTNAME}/" "${env_file}"
  else
    printf '\nCMS_SERVER_NAME=%s\n' "${CMS_HOSTNAME}" >> "${env_file}"
  fi
  echo "Set CMS_SERVER_NAME=${CMS_HOSTNAME} in ${env_file}"
}

write_trusted_proxy() {
  local custom_dir="${XIBO_ROOT}/shared/cms/custom"
  local settings="${custom_dir}/settings-custom.php"
  mkdir -p "${custom_dir}"
  if [[ -f "${settings}" ]] && grep -q 'trustedProxyIps' "${settings}"; then
    if ! grep -q '127.0.0.1' "${settings}"; then
      echo "Update ${settings}: add 127.0.0.1 to \$trustedProxyIps (Caddy on localhost)." >&2
      exit 1
    fi
    echo "Trusted proxy already configured in ${settings}"
    return 0
  fi
  if [[ -f "${settings}" ]]; then
    cat >> "${settings}" <<'EOF'

// mmek: trust host Caddy reverse proxy (loopback)
$trustedProxyIps = '127.0.0.1';
EOF
  else
    cat > "${settings}" <<'EOF'
<?php
// mmek: trust host Caddy reverse proxy (loopback)
// See https://docs.xibosignage.com/setup-docs/cms-installation/self-hosted-cms
$trustedProxyIps = '127.0.0.1';
EOF
  fi
  echo "Wrote trusted proxy setting to ${settings}"
}

ensure_go() {
  export PATH="/usr/local/go/bin:${PATH}"
  if command -v go >/dev/null 2>&1; then
    echo "Using Go $(go version)"
    return 0
  fi
  echo "==> Installing Go ${GO_VERSION} to /usr/local/go"
  local archive="/tmp/go${GO_VERSION}.linux-amd64.tar.gz"
  curl -fsSL -o "${archive}" "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz"
  rm -rf /usr/local/go
  tar -C /usr/local -xzf "${archive}"
  rm -f "${archive}"
  export PATH="/usr/local/go/bin:${PATH}"
  go version
}

caddy_has_route53() {
  command -v caddy >/dev/null 2>&1 \
    && caddy list-modules 2>/dev/null | grep -q 'dns.providers.route53'
}

install_caddy_with_route53() {
  # Apt package provides the systemd unit; binary is replaced with an xcaddy build
  # that includes github.com/caddy-dns/route53 for DNS-01.
  if ! command -v caddy >/dev/null 2>&1; then
    echo "==> Installing Caddy package (systemd unit)"
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
      | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
      | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    apt-get update -y
    apt-get install -y caddy
  fi

  if caddy_has_route53; then
    echo "Caddy already includes dns.providers.route53: $(caddy version 2>/dev/null || true)"
  else
    echo "==> Building Caddy with Route 53 DNS module (xcaddy)"
    ensure_go
    apt-get install -y git curl ca-certificates
    export GOPATH="${GOPATH:-/root/go}"
    export PATH="${PATH}:${GOPATH}/bin"
    go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest
    local build_dir
    build_dir="$(mktemp -d /tmp/caddy-build.XXXXXX)"
    (
      cd "${build_dir}"
      xcaddy build --with github.com/caddy-dns/route53
      install -m 755 caddy /usr/bin/caddy
    )
    rm -rf "${build_dir}"
    setcap cap_net_bind_service=+ep /usr/bin/caddy || true
    if ! caddy_has_route53; then
      echo "Built Caddy is missing dns.providers.route53." >&2
      exit 1
    fi
    echo "Installed $(caddy version)"
  fi

  echo "==> Installing Caddyfile for ${CMS_HOSTNAME} (DNS-01 / Route 53)"
  local zone_line=""
  if [[ -n "${AWS_HOSTED_ZONE_ID:-}" ]]; then
    zone_line="			hosted_zone_id ${AWS_HOSTED_ZONE_ID}"
  fi
  cat > /etc/caddy/Caddyfile <<EOF
# Generated by enable-cms-tls.sh — Let's Encrypt DNS-01 (Route 53)
${CMS_HOSTNAME} {
	tls {
		dns route53 {
${zone_line}
		}
	}
	reverse_proxy 127.0.0.1:${CMS_LOOPBACK_PORT}
}
EOF
  chmod 644 /etc/caddy/Caddyfile
  if ! grep -q "${CMS_HOSTNAME}" /etc/caddy/Caddyfile; then
    echo "Caddyfile missing hostname ${CMS_HOSTNAME}." >&2
    exit 1
  fi

  mkdir -p /etc/systemd/system/caddy.service.d
  cat > /etc/systemd/system/caddy.service.d/acme-env.conf <<EOF
[Service]
EnvironmentFile=${ACME_ENV_FILE}
EOF
  systemctl daemon-reload
}

configure_ufw() {
  if ! command -v ufw >/dev/null 2>&1; then
    echo "ufw not installed; skip firewall rules."
    return 0
  fi

  local lock_file="/etc/mmek/tailscale-ufw.lock"
  if [[ -f "${lock_file}" ]]; then
    # install-tailscale.sh already scoped 22/80/443/9505 to tailscale0 + LAN.
    # Do not re-open those ports to Anywhere on TLS re-runs.
    echo "==> Tailscale UFW lockdown present (${lock_file}); skipping world-open allows"
    local lan_cidr
    lan_cidr="$(grep -E '^FACILITY_LAN_CIDR=' "${lock_file}" | head -n1 | cut -d= -f2- || true)"
    if [[ -n "${lan_cidr}" ]]; then
      ufw allow in on tailscale0 to any port 80 proto tcp comment 'HTTP redirect via Tailscale' >/dev/null || true
      ufw allow from "${lan_cidr}" to any port 80 proto tcp comment 'HTTP redirect via facility LAN' >/dev/null || true
      ufw allow in on tailscale0 to any port 443 proto tcp comment 'CMS HTTPS via Tailscale' >/dev/null || true
      ufw allow from "${lan_cidr}" to any port 443 proto tcp comment 'CMS HTTPS via facility LAN' >/dev/null || true
      ufw allow in on tailscale0 to any port 9505 proto tcp comment 'XMR via Tailscale' >/dev/null || true
      ufw allow from "${lan_cidr}" to any port 9505 proto tcp comment 'XMR via facility LAN' >/dev/null || true
    fi
    ufw --force enable >/dev/null || true
    ufw status verbose | head -n 40 || true
    return 0
  fi

  echo "==> Ensuring UFW allows HTTPS/XMR (and HTTP redirect)"
  ufw allow OpenSSH >/dev/null || true
  ufw allow 80/tcp comment 'Xibo CMS HTTP redirect' >/dev/null || true
  ufw allow 443/tcp comment 'Xibo CMS HTTPS' >/dev/null || true
  ufw allow 9505/tcp comment 'Xibo XMR' >/dev/null || true
  ufw --force enable >/dev/null || true
  ufw status verbose | head -n 40 || true
}

require_acme_env

echo "==> Binding cms-web to loopback :${CMS_LOOPBACK_PORT}"
bind_cms_web_loopback "${COMPOSE_FILE}"
set_cms_server_name
write_trusted_proxy

echo "==> Recreating Xibo stack with new port publish"
cd "${XIBO_ROOT}"
docker compose up -d

install_caddy_with_route53
configure_ufw

echo "==> Validating Caddyfile and starting Caddy"
# Load env for validate (same vars systemd will use).
set -a
# shellcheck source=/dev/null
source "${ACME_ENV_FILE}"
set +a
caddy validate --config /etc/caddy/Caddyfile
systemctl enable --now caddy
systemctl reload caddy || systemctl restart caddy

echo
echo "TLS enablement complete (Let's Encrypt DNS-01 / Route 53)."
echo "  Public UI:  https://${CMS_HOSTNAME}/"
echo "  Upstream:   http://127.0.0.1:${CMS_LOOPBACK_PORT}/ (cms-web loopback)"
echo "  Sync URL:   http://127.0.0.1:${CMS_LOOPBACK_PORT}  (prefer loopback in cms-sync.env)"
echo "  ACME env:   ${ACME_ENV_FILE}"

CMS_SYNC_ENV="${MMEK_ENV_FILE:-/etc/mmek/cms-sync.env}"
if [[ -f "${CMS_SYNC_ENV}" ]]; then
  if grep -q '^XIBO_CMS_TLS_HOST=' "${CMS_SYNC_ENV}"; then
    sed -i "s|^XIBO_CMS_TLS_HOST=.*|XIBO_CMS_TLS_HOST=${CMS_HOSTNAME}|" "${CMS_SYNC_ENV}"
  else
    printf '\n# Public hostname for sync when Force HTTPS is enabled (see xibo_client.py)\nXIBO_CMS_TLS_HOST=%s\n' \
      "${CMS_HOSTNAME}" >> "${CMS_SYNC_ENV}"
  fi
  echo "  Set XIBO_CMS_TLS_HOST=${CMS_HOSTNAME} in ${CMS_SYNC_ENV}"
fi
echo
echo "Verify (LAN DNS must resolve ${CMS_HOSTNAME} to this host):"
echo "  curl -fsSI https://${CMS_HOSTNAME}/login"
echo
echo "Then in the CMS UI:"
echo "  1. Settings → Network: enable Force HTTPS"
echo "  2. Settings → Displays: XMR public address ="
echo "       tcp://${CMS_HOSTNAME}:9505"
echo "  3. Leave XMR WebSocket empty (players use https://${CMS_HOSTNAME}/xmr)"
echo
echo "If ACME fails, check IAM Route53 rights and: journalctl -u caddy -e"
