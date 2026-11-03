#!/bin/bash -e
# Install Arexibo inside the image rootfs.
# Prefer a CI-prefetched local .deb (avoids Cloudflare 403 from chroot on
# dl.xiboplayer.org). Fall back to the apt repo when the deb is absent.
set -euo pipefail

STAGE_SUBDIR="$(cd "$(dirname "$0")" && pwd)"
FILES_DIR="$(cd "${STAGE_SUBDIR}/../../files" && pwd)"
PIN_FILE="${STAGE_SUBDIR}/AREXIBO_VERSION"
LOCAL_DEB="${STAGE_SUBDIR}/arexibo.deb"
PIN=""
if [[ -f "${PIN_FILE}" ]]; then
	PIN="$(tr -d '[:space:]' < "${PIN_FILE}")"
fi

install -d -m 0755 "${ROOTFS_DIR}/usr/share/keyrings" "${ROOTFS_DIR}/etc/mmek" "${ROOTFS_DIR}/tmp"
install -m 0644 "${FILES_DIR}/xiboplayer-GPG-KEY.asc" "${ROOTFS_DIR}/usr/share/keyrings/xiboplayer.asc"

if [[ -f "${LOCAL_DEB}" ]]; then
	install -m 0644 "${LOCAL_DEB}" "${ROOTFS_DIR}/tmp/arexibo.deb"
	on_chroot << EOF
set -euo pipefail
apt-get update
apt-get install -y /tmp/arexibo.deb
rm -f /tmp/arexibo.deb
INSTALLED="\$(dpkg-query -W -f='\${Version}' arexibo)"
printf '%s\n' "\${INSTALLED}" > /etc/mmek/arexibo-package-version
PIN="${PIN}"
if [[ -n "\${PIN}" && "\${INSTALLED}" != "\${PIN}" ]]; then
  echo "Arexibo version mismatch: wanted \${PIN}, got \${INSTALLED}" >&2
  exit 1
fi
command -v arexibo >/dev/null
EOF
else
	on_chroot << EOF
set -euo pipefail
curl -fsSL -A 'MMEK-player-image/1.0' https://dl.xiboplayer.org/deb/GPG-KEY.asc \
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
fi
