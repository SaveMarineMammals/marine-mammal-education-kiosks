#!/usr/bin/env bash
# Serve server.kiosks.local.belize.savemarinemammals.com → this host's Tailscale
# IPv4 via dnsmasq on tailscale0. Pair with Tailscale admin split DNS pointing
# at this 100.x for domain kiosks.local.belize.savemarinemammals.com.
#
# Do not put 100.x or *.ts.net CNAMEs in Route 53 — keep the LAN A record there.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

CMS_HOSTNAME="${CMS_HOSTNAME:-server.kiosks.local.belize.savemarinemammals.com}"
SPLIT_DOMAIN="${SPLIT_DOMAIN:-kiosks.local.belize.savemarinemammals.com}"
CONF_PATH=/etc/dnsmasq.d/mmek-cms.conf

if ! command -v tailscale >/dev/null 2>&1; then
  echo "error: tailscale not installed; run install-tailscale.sh first" >&2
  exit 2
fi

TS_IP="$(tailscale ip -4)"
if [[ -z "${TS_IP}" || "${TS_IP}" != 100.* ]]; then
  echo "error: expected a Tailscale IPv4 (100.x); got '${TS_IP:-empty}'" >&2
  exit 2
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y dnsmasq dnsutils

cat > "${CONF_PATH}" <<EOF
# Managed by install-cms-split-dns.sh — Tailscale split-DNS answer for CMS hostname
address=/${CMS_HOSTNAME}/${TS_IP}
interface=tailscale0
bind-interfaces
no-resolv
EOF
chmod 0644 "${CONF_PATH}"

# install-tailscale.sh historically opened 22/80/443/9505 only; DNS is required
# for split-DNS clients to reach this nameserver.
if command -v ufw >/dev/null 2>&1; then
  ufw allow in on tailscale0 to any port 53 proto udp comment 'CMS split-DNS via Tailscale' || true
  ufw allow in on tailscale0 to any port 53 proto tcp comment 'CMS split-DNS via Tailscale' || true
fi

systemctl enable --now dnsmasq
systemctl restart dnsmasq

echo "==> Checking ${CMS_HOSTNAME} via ${TS_IP}"
ANSWER="$(dig @"${TS_IP}" "${CMS_HOSTNAME}" +short | head -n1 || true)"
if [[ "${ANSWER}" != "${TS_IP}" ]]; then
  echo "error: dig @${TS_IP} ${CMS_HOSTNAME} returned '${ANSWER:-empty}' (expected ${TS_IP})" >&2
  ss -ulnp | grep ':53' || true
  journalctl -u dnsmasq -n 40 --no-pager -l || true
  exit 1
fi

echo
echo "CMS split DNS ready."
echo "  nameserver: ${TS_IP} (this host on tailscale0)"
echo "  answers:    ${CMS_HOSTNAME} → ${TS_IP}"
echo
echo "Next (Tailscale admin → DNS):"
echo "  1. MagicDNS: on"
echo "  2. Add nameserver → Custom → ${TS_IP}"
echo "  3. Restrict to domain: ${SPLIT_DOMAIN}"
echo "  4. Keep Route 53 A for ${CMS_HOSTNAME} on the facility LAN IP (not 100.x)."
