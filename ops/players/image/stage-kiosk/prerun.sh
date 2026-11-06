#!/bin/bash -e
# Copy rootfs from the previous pi-gen stage when this stage is first entered.
if [ ! -d "${ROOTFS_DIR}" ]; then
	copy_previous
fi
