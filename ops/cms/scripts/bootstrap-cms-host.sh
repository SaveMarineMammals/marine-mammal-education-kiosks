#!/usr/bin/env bash
# Bootstrap an Ubuntu Server host for Xibo CMS (Docker).
# Run as a sudo-capable user on the CMS mini PC after first login.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

export DEBIAN_FRONTEND=noninteractive

echo "==> Updating apt indexes and applying upgrades"
apt-get update -y
apt-get upgrade -y

echo "==> Installing Docker Engine + Compose plugin and helpers"
apt-get install -y \
  ca-certificates \
  curl \
  docker.io \
  docker-compose-v2 \
  ufw \
  unattended-upgrades \
  apt-listchanges

echo "==> Enabling Docker"
systemctl enable --now docker

# Allow the invoking sudo user to run docker without sudo after re-login.
if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  usermod -aG docker "${SUDO_USER}"
  echo "Added ${SUDO_USER} to group docker (log out/in to take effect)."
fi

echo "==> Configuring unattended security updates"
dpkg-reconfigure -f noninteractive unattended-upgrades || true

echo "==> Configuring UFW (SSH, HTTP redirect, HTTPS, XMR 9505)"
ufw allow OpenSSH
ufw allow 80/tcp comment 'Xibo CMS HTTP redirect'
ufw allow 443/tcp comment 'Xibo CMS HTTPS'
ufw allow 9505/tcp comment 'Xibo XMR'
# --force enables without interactive prompt
ufw --force enable
ufw status verbose

echo
echo "Bootstrap complete."
echo "Next:"
echo "  1. Log out and back in (or: newgrp docker)"
echo "  2. Run: sudo ./install-xibo-cms.sh"
echo "  3. Run: sudo ./enable-cms-tls.sh  (after DNS for the CMS hostname)"
echo "  4. Run: sudo FACILITY_LAN_CIDR=… TS_AUTHKEY=… ./install-tailscale.sh"
echo "     (see ops/runbooks/facility-tailscale.md)"
echo "  5. Open https://server.kiosks.local.belize.savemarinemammals.com/ and change the xibo_admin password"
echo "  6. Run: sudo ./install-security-updates.sh  (off-hours patches + admin alerts)"
echo "     see ops/runbooks/security-patching.md"
