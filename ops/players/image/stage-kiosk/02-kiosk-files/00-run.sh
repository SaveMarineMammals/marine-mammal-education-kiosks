#!/bin/bash -e
# Install MMEK kiosk scripts and units into the image rootfs.
# FILES_DIR is the recipe files/ directory (sibling of stage-kiosk).
set -euo pipefail

STAGE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FILES_DIR="$(cd "${STAGE_DIR}/../files" && pwd)"
VERSION_FILE="$(cd "${STAGE_DIR}/.." && pwd)/VERSION"

install -d "${ROOTFS_DIR}/etc/mmek"
install -d "${ROOTFS_DIR}/usr/local/sbin"
install -d "${ROOTFS_DIR}/etc/systemd/system"
install -d "${ROOTFS_DIR}/boot/firmware"

install -m 0755 "${FILES_DIR}/first-boot-kiosk.sh" "${ROOTFS_DIR}/usr/local/sbin/first-boot-kiosk.sh"
install -m 0755 "${FILES_DIR}/mmek-arexibo-start" "${ROOTFS_DIR}/usr/local/sbin/mmek-arexibo-start"
install -m 0644 "${FILES_DIR}/first-boot-kiosk.service" "${ROOTFS_DIR}/etc/systemd/system/first-boot-kiosk.service"
install -m 0644 "${FILES_DIR}/mmek-kiosk-display.service" "${ROOTFS_DIR}/etc/systemd/system/mmek-kiosk-display.service"
install -m 0644 "${FILES_DIR}/arexibo.service" "${ROOTFS_DIR}/etc/systemd/system/arexibo.service"
install -m 0644 "${FILES_DIR}/kiosk.conf.example" "${ROOTFS_DIR}/etc/mmek/kiosk.conf.example"

if [[ -f "${VERSION_FILE}" ]]; then
  install -m 0644 "${VERSION_FILE}" "${ROOTFS_DIR}/etc/mmek/image-recipe-version"
fi
