#!/bin/bash -e
# Install Arexibo inside the image rootfs.
# Prefer a CI-prefetched local .deb (mirrored GitHub Release; see
# vendor/arexibo.manifest.yaml). Fall back to apt only when the deb is absent.
# All paths must stay under stage-kiosk/ (only that dir is Docker-mounted).
set -euo pipefail

STAGE_SUBDIR="$(cd "$(dirname "$0")" && pwd)"
STAGE_DIR="$(cd "${STAGE_SUBDIR}/.." && pwd)"
FILES_DIR="${STAGE_DIR}/files"
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
# Real runtime deps declared by romoloman .debs that apt can satisfy on Trixie.
apt-get install -y xinput
# romoloman 0.6.5 Depends on libqt6gui6t64 / libqt6widgets6t64, but Debian
# Trixie arm64 ships those ABIs as libqt6gui6 / libqt6widgets6 (no t64 package
# names). Optional pulseaudio* deps are also skipped — kiosk audio uses the
# image stack as-is. Install with --force-depends, then hold the package so
# apt --fix-broken does not remove it.
dpkg -i --force-depends /tmp/arexibo.deb
rm -f /tmp/arexibo.deb
apt-mark hold arexibo
INSTALLED="\$(dpkg-query -W -f='\${Version}' arexibo)"
printf '%s\n' "\${INSTALLED}" > /etc/mmek/arexibo-package-version
PIN="${PIN}"
if [[ -n "\${PIN}" && "\${INSTALLED}" != "\${PIN}" ]]; then
  echo "Arexibo version mismatch: wanted \${PIN}, got \${INSTALLED}" >&2
  exit 1
fi
command -v arexibo >/dev/null
arexibo --version >/dev/null
EOF
else
	on_chroot << EOF
set -euo pipefail
# Fallback only: xiboplayer.org apt (may lag the mirrored romoloman pin).
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
