#!/bin/bash
# Live retrofit: install Tailscale (if needed) and join as tag:mmek-players.
# Usage (on the Pi):
#   sudo TS_AUTHKEY='tskey-auth-…' ./join-tailscale.sh
# Do not commit real auth keys. New flashes join via first-boot + kiosk.conf.
#
# On some fleet images Arexibo is held with apt-unsatisfiable Qt Depends
# (binaries still run). Plain `apt-get install tailscale` then fails. This
# script falls back to apt-get download + dpkg -i for iptables + tailscale.
set -euo pipefail

TAG="tag:mmek-players"
HOSTNAME_TS="${TS_HOSTNAME:-$(hostname -s)}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

export DEBIAN_FRONTEND=noninteractive

ensure_tailscale_apt_source() {
  . /etc/os-release
  local ts_codename="${VERSION_CODENAME:-bookworm}"
  local ts_base="https://pkgs.tailscale.com/stable/debian"
  if [[ ! -f /usr/share/keyrings/tailscale-archive-keyring.gpg ]]; then
    if ! curl -fsSL "${ts_base}/${ts_codename}.noarmor.gpg" \
      -o /usr/share/keyrings/tailscale-archive-keyring.gpg; then
      echo "Falling back to bookworm keyring" >&2
      ts_codename=bookworm
      curl -fsSL "${ts_base}/${ts_codename}.noarmor.gpg" \
        -o /usr/share/keyrings/tailscale-archive-keyring.gpg
    fi
  fi
  if [[ ! -f /etc/apt/sources.list.d/tailscale.list ]]; then
    . /etc/os-release
    ts_codename="${VERSION_CODENAME:-bookworm}"
    if ! curl -fsSL "${ts_base}/${ts_codename}.tailscale-keyring.list" \
      -o /etc/apt/sources.list.d/tailscale.list; then
      ts_codename=bookworm
      curl -fsSL "${ts_base}/${ts_codename}.tailscale-keyring.list" \
        -o /etc/apt/sources.list.d/tailscale.list
    fi
  fi
  chmod 0644 /usr/share/keyrings/tailscale-archive-keyring.gpg \
    /etc/apt/sources.list.d/tailscale.list
  apt-get update -y
}

install_tailscale_via_dpkg() {
  # Bypass apt's refusal to install anything while held arexibo has
  # unsatisfiable Depends (libqt6*t64 not in the archive for this image).
  local tmp
  tmp="$(mktemp -d /tmp/mmek-ts-debs.XXXXXX)"
  # shellcheck disable=SC2064
  trap "rm -rf '${tmp}'" RETURN
  echo "==> Downloading iptables + tailscale debs (avoiding apt resolver)"
  (
    cd "${tmp}"
    apt-get download iptables libip4tc2 libip6tc2
    apt-get download tailscale
    echo "==> dpkg -i locally downloaded packages"
    dpkg -i ./*.deb
  )
  command -v tailscale >/dev/null
  command -v tailscaled >/dev/null
}

if ! command -v tailscale >/dev/null 2>&1; then
  echo "==> Installing Tailscale from pkgs.tailscale.com"
  ensure_tailscale_apt_source
  if ! apt-get install -y tailscale; then
    echo "==> apt-get install failed (often held arexibo Qt deps); using dpkg fallback" >&2
    install_tailscale_via_dpkg
  fi
else
  echo "==> Tailscale already installed: $(tailscale version | head -n1)"
fi

systemctl enable --now tailscaled

if [[ -z "${TS_AUTHKEY:-}" ]]; then
  echo "ERROR: export TS_AUTHKEY first (tag:mmek-players auth key)" >&2
  exit 2
fi

up_args=(
  up
  --hostname="${HOSTNAME_TS}"
  --advertise-tags="${TAG}"
  --accept-dns=true
  --auth-key="${TS_AUTHKEY}"
)
if [[ "${TS_RESET:-0}" == "1" ]]; then
  up_args+=(--reset)
fi

echo "==> tailscale up --hostname=${HOSTNAME_TS} --advertise-tags=${TAG} --accept-dns=true --auth-key=****"
tailscale "${up_args[@]}"

echo "==> ipv4: $(tailscale ip -4 2>/dev/null || echo pending)"
tailscale status || true
echo "==> CMS hostname resolution:"
getent hosts server.kiosks.local.belize.savemarinemammals.com || true
systemctl is-active arexibo.service || true
