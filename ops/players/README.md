# Raspberry Pi players

## Target stack

- Raspberry Pi (model TBD per site; prefer Pi 4/5 class for 1080p video)
- Linux OS suitable for Xibo Linux Player
- **Xibo Linux Player** enrolled against the central CMS
- Display: TV via HDMI, typically 1920×1080

## Bootstrap outline

1. Flash OS image; enable SSH for initial setup only (lock down later).
2. Set hostname: `kiosk-<location>-<nn>` (see `ops/networking/`).
3. Configure static DHCP reservation or static IP.
4. Install Xibo Linux Player; point at CMS URL.
5. Authorize the display in CMS; assign to a **display group** by location/role (`lobby`, not exhibit names).
6. Set display profile (resolution, orientation, stats).
7. Optional: kiosk watchdog (auto-restart player on crash), unattended-upgrades policy, disable screen blanking.
8. Verify a known test layout plays offline after CMS cache (see runbook `offline-cache.md`).

## Image / config as code

Document the exact OS version, player version, and CMS display settings used in production here as the fleet grows. Prefer a repeatable image or Ansible/cloud-init later; start with a checked checklist per device.

## Checklist (new Pi)

- [ ] Hostname set
- [ ] Network + CMS reachable
- [ ] Player registered and licensed/authorized as required
- [ ] Display group assigned
- [ ] Test layout plays
- [ ] Reboot persistence confirmed
