#!/bin/bash -e
# Install Arexibo inside the image chroot (optional pin via AREXIBO_VERSION file).
set -euo pipefail

STAGE_SUBDIR="$(cd "$(dirname "$0")" && pwd)"
PIN_FILE="${STAGE_SUBDIR}/AREXIBO_VERSION"
PIN=""
if [[ -f "${PIN_FILE}" ]]; then
	PIN="$(tr -d '[:space:]' < "${PIN_FILE}")"
fi

on_chroot << EOF
set -euo pipefail
install -d -m 0755 /usr/share/keyrings /etc/mmek
curl -fsSL https://dl.xiboplayer.org/deb/GPG-KEY.asc \
  | tee /usr/share/keyrings/xiboplayer.asc >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/xiboplayer.asc] https://dl.xiboplayer.org/deb/debian/trixie ./' \
  > /etc/apt/sources.list.d/xiboplayer.list
apt-get update
PIN="${PIN}"
if [[ -n "\${PIN}" ]]; then
  apt-get install -y "arexibo=\${PIN}"
else
  apt-get install -y arexibo
fi
dpkg-query -W -f='\${Version}\\n' arexibo > /etc/mmek/arexibo-package-version
command -v arexibo >/dev/null
EOF
