#!/bin/bash -e
# Install Tailscale from pkgs.tailscale.com (join on first-boot with TS_AUTHKEY).
# https://tailscale.com/download/linux/debian-trixie
set -euo pipefail

chmod 1777 /tmp

if command -v tailscale >/dev/null 2>&1; then
  echo "Tailscale already installed: $(tailscale version | head -n1)"
else
  . /etc/os-release
  TS_CODENAME="${VERSION_CODENAME:-trixie}"
  TS_BASE="https://pkgs.tailscale.com/stable/debian"
  if ! curl -fsSL "${TS_BASE}/${TS_CODENAME}.noarmor.gpg" \
    -o /usr/share/keyrings/tailscale-archive-keyring.gpg; then
    echo "Tailscale apt key for ${TS_CODENAME} unavailable; falling back to bookworm" >&2
    TS_CODENAME=bookworm
    curl -fsSL "${TS_BASE}/${TS_CODENAME}.noarmor.gpg" \
      -o /usr/share/keyrings/tailscale-archive-keyring.gpg
  fi
  curl -fsSL "${TS_BASE}/${TS_CODENAME}.tailscale-keyring.list" \
    -o /etc/apt/sources.list.d/tailscale.list
  chmod 0644 /usr/share/keyrings/tailscale-archive-keyring.gpg \
    /etc/apt/sources.list.d/tailscale.list
  apt-get update -y
  apt-get install -y tailscale
fi

command -v tailscale >/dev/null
command -v tailscaled >/dev/null
systemctl enable tailscaled
# Do not run `tailscale up` at image build time — first-boot uses TS_AUTHKEY.
printf '%s\n' "$(tailscale version | head -n1)" > /etc/mmek/tailscale-package-version
