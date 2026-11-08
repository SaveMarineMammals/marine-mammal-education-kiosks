#!/usr/bin/env bash
# Join the facility CMS host to Tailscale (tag:mmek-cms) and optionally tighten UFW.
# Run as a sudo-capable user on the CMS mini PC after bootstrap (LAN or console).
#
# Env:
#   TS_AUTHKEY          Tagged auth key for tag:mmek-cms (optional; interactive login if unset)
#   FACILITY_LAN_CIDR   Required when TIGHTEN_UFW=1 (e.g. 192.168.1.0/24)
#   TIGHTEN_UFW         Default 1 — restrict 22/443/9505 to tailscale0 + LAN CIDR
#   TS_HOSTNAME         Override Tailscale hostname (default: system hostname)
#   TS_LOGIN_SERVER     Optional custom coordination server
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

TIGHTEN_UFW="${TIGHTEN_UFW:-1}"
TS_HOSTNAME="${TS_HOSTNAME:-$(hostname -s)}"
LOCK_FILE="/etc/mmek/tailscale-ufw.lock"
TAG="tag:mmek-cms"

export DEBIAN_FRONTEND=noninteractive

install_tailscale_pkg() {
  if command -v tailscale >/dev/null 2>&1; then
    echo "==> Tailscale already installed: $(tailscale version | head -n1)"
    return 0
  fi

  echo "==> Installing Tailscale from pkgs.tailscale.com"
  # Official Ubuntu/Debian install steps:
  # https://tailscale.com/download/linux/ubuntu-2404
  . /etc/os-release
  curl -fsSL "https://pkgs.tailscale.com/stable/ubuntu/${VERSION_CODENAME}.noarmor.gpg" \
    | tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
  curl -fsSL "https://pkgs.tailscale.com/stable/ubuntu/${VERSION_CODENAME}.tailscale-keyring.list" \
    | tee /etc/apt/sources.list.d/tailscale.list >/dev/null
  apt-get update -y
  apt-get install -y tailscale
}

bring_up() {
  systemctl enable --now tailscaled

  local up_args=(
    up
    --hostname="${TS_HOSTNAME}"
    --advertise-tags="${TAG}"
    --accept-dns=true
  )
  if [[ -n "${TS_LOGIN_SERVER:-}" ]]; then
    up_args+=(--login-server="${TS_LOGIN_SERVER}")
  fi
  if [[ -n "${TS_AUTHKEY:-}" ]]; then
    up_args+=(--auth-key="${TS_AUTHKEY}")
  fi

  if [[ -n "${TS_AUTHKEY:-}" ]]; then
    echo "==> tailscale up --hostname=${TS_HOSTNAME} --advertise-tags=${TAG} --accept-dns=true --auth-key=****"
  else
    echo "==> tailscale up --hostname=${TS_HOSTNAME} --advertise-tags=${TAG} --accept-dns=true (interactive)"
  fi
  tailscale "${up_args[@]}"
}

delete_open_anywhere_rules() {
  # Drop world-open allows from bootstrap / enable-cms-tls so scoped rules replace them.
  ufw delete allow OpenSSH >/dev/null 2>&1 || true
  ufw delete allow 22/tcp >/dev/null 2>&1 || true
  ufw delete allow 80/tcp >/dev/null 2>&1 || true
  ufw delete allow 443/tcp >/dev/null 2>&1 || true
  ufw delete allow 9505/tcp >/dev/null 2>&1 || true
}

tighten_ufw() {
  if [[ "${TIGHTEN_UFW}" != "1" ]]; then
    echo "==> Skipping UFW tighten (TIGHTEN_UFW=${TIGHTEN_UFW})"
    return 0
  fi
  if [[ -z "${FACILITY_LAN_CIDR:-}" ]]; then
    echo "error: FACILITY_LAN_CIDR is required when TIGHTEN_UFW=1 (e.g. 192.168.1.0/24)" >&2
    exit 2
  fi
  if ! command -v ufw >/dev/null 2>&1; then
    echo "error: ufw not installed; run bootstrap-cms-host.sh first" >&2
    exit 2
  fi

  echo "==> Tightening UFW: 22/443/9505 (+80 redirect) on tailscale0 and ${FACILITY_LAN_CIDR}"
  delete_open_anywhere_rules

  ufw allow in on tailscale0 to any port 22 proto tcp comment 'SSH via Tailscale' || true
  ufw allow from "${FACILITY_LAN_CIDR}" to any port 22 proto tcp comment 'SSH via facility LAN' || true

  ufw allow in on tailscale0 to any port 80 proto tcp comment 'HTTP redirect via Tailscale' || true
  ufw allow from "${FACILITY_LAN_CIDR}" to any port 80 proto tcp comment 'HTTP redirect via facility LAN' || true

  ufw allow in on tailscale0 to any port 443 proto tcp comment 'CMS HTTPS via Tailscale' || true
  ufw allow from "${FACILITY_LAN_CIDR}" to any port 443 proto tcp comment 'CMS HTTPS via facility LAN' || true

  ufw allow in on tailscale0 to any port 9505 proto tcp comment 'XMR via Tailscale' || true
  ufw allow from "${FACILITY_LAN_CIDR}" to any port 9505 proto tcp comment 'XMR via facility LAN' || true

  ufw --force enable
  install -d -m 0755 /etc/mmek
  cat > "${LOCK_FILE}" <<EOF
# Written by install-tailscale.sh — enable-cms-tls.sh skips world-open UFW allows when present.
FACILITY_LAN_CIDR=${FACILITY_LAN_CIDR}
tightened_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
  chmod 0644 "${LOCK_FILE}"
}

install_tailscale_pkg
bring_up
tighten_ufw

echo
echo "Tailscale CMS join complete."
echo "  hostname: ${TS_HOSTNAME} (${TAG})"
echo "  ipv4:     $(tailscale ip -4 2>/dev/null || echo '(pending)')"
tailscale status || true
echo
if [[ -f "${LOCK_FILE}" ]]; then
  echo "UFW lockdown marker: ${LOCK_FILE}"
  ufw status verbose || true
fi
echo
echo "Next: configure Tailscale split DNS for server.kiosks.local.belize.savemarinemammals.com"
echo "      → this host's Tailscale IPv4 (see ops/runbooks/facility-tailscale.md)."
