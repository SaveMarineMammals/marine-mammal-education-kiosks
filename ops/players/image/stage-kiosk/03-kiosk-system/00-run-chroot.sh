#!/bin/bash -e
# Create kiosk user, autologin X session, HDMI preference, enable first-boot unit.
set -euo pipefail

if ! id -u kiosk >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash --groups video,render,input,audio kiosk
fi

install -d -m 0755 /home/kiosk
install -m 0755 /dev/stdin /home/kiosk/.xinitrc <<'EOF'
#!/bin/sh
xset s off || true
xset -dpms || true
xset s noblank || true
exec openbox-session
EOF
chown -R kiosk:kiosk /home/kiosk

install -d -m 0755 /var/lib/arexibo /var/lib/mmek
chown -R kiosk:kiosk /var/lib/arexibo

# Prefer 1920x1080 for Glance & Match (panel is native 4K).
BOOT_CFG=""
for candidate in /boot/firmware/config.txt /boot/config.txt; do
  if [[ -f "${candidate}" ]]; then
    BOOT_CFG="${candidate}"
    break
  fi
done
if [[ -n "${BOOT_CFG}" ]]; then
  if ! grep -q 'hdmi_group=1' "${BOOT_CFG}"; then
    cat >> "${BOOT_CFG}" <<'EOF'

# MMEK kiosk: force CEA 1080p60 (Glance & Match canvas)
hdmi_group=1
hdmi_mode=16
hdmi_force_hotplug=1
EOF
  fi
fi

# Disable console blanking
if [[ -f /etc/kbd/config ]]; then
  sed -i 's/^BLANK_TIME=.*/BLANK_TIME=0/' /etc/kbd/config || true
fi
mkdir -p /etc/systemd/system/getty@tty1.service.d
# Keep tty1 available for recovery; graphical session uses vt7 via xinit.

systemctl enable first-boot-kiosk.service
# Display + arexibo are enabled by first-boot after kiosk.conf is present.
systemctl disable arexibo.service mmek-kiosk-display.service 2>/dev/null || true

# Unattended security updates (no automatic reboot by default)
echo 'Unattended-Upgrade::Automatic-Reboot "false";' \
  > /etc/apt/apt.conf.d/52unattended-reboot-mmek
