#!/bin/bash -e
# Install MMEK kiosk scripts and units into the image rootfs.
# Files live under stage-kiosk/files (must be inside the Docker-mounted stage).
set -euo pipefail

STAGE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FILES_DIR="${STAGE_DIR}/files"
VERSION_FILE="${STAGE_DIR}/VERSION"

install -d "${ROOTFS_DIR}/etc/mmek"
install -d "${ROOTFS_DIR}/usr/local/sbin"
install -d "${ROOTFS_DIR}/etc/systemd/system"
install -d "${ROOTFS_DIR}/boot/firmware"
install -d "${ROOTFS_DIR}/etc/X11"
install -d "${ROOTFS_DIR}/etc/X11/xorg.conf.d"

install -m 0755 "${FILES_DIR}/first-boot-kiosk.sh" "${ROOTFS_DIR}/usr/local/sbin/first-boot-kiosk.sh"
install -m 0755 "${FILES_DIR}/mmek-arexibo-start" "${ROOTFS_DIR}/usr/local/sbin/mmek-arexibo-start"
install -m 0755 "${FILES_DIR}/mmek-select-kms-card.sh" "${ROOTFS_DIR}/usr/local/sbin/mmek-select-kms-card.sh"
install -m 0644 "${FILES_DIR}/first-boot-kiosk.service" "${ROOTFS_DIR}/etc/systemd/system/first-boot-kiosk.service"
install -m 0644 "${FILES_DIR}/mmek-kiosk-display.service" "${ROOTFS_DIR}/etc/systemd/system/mmek-kiosk-display.service"
install -m 0644 "${FILES_DIR}/arexibo.service" "${ROOTFS_DIR}/etc/systemd/system/arexibo.service"
install -m 0644 "${FILES_DIR}/kiosk.conf.example" "${ROOTFS_DIR}/etc/mmek/kiosk.conf.example"
install -m 0644 "${FILES_DIR}/Xwrapper.config" "${ROOTFS_DIR}/etc/X11/Xwrapper.config"
install -m 0644 "${FILES_DIR}/99-mmek-fbdev-ignore.conf" "${ROOTFS_DIR}/etc/X11/xorg.conf.d/99-mmek-fbdev-ignore.conf"
install -m 0755 "${FILES_DIR}/xinitrc" "${ROOTFS_DIR}/etc/mmek/xinitrc"

if [[ -f "${VERSION_FILE}" ]]; then
  install -m 0644 "${VERSION_FILE}" "${ROOTFS_DIR}/etc/mmek/image-recipe-version"
fi
