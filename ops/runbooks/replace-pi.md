# Runbook: replace a failed Raspberry Pi

1. Note the failed unit’s hostname, display group, CMS display name, and MAC.
2. Flash the same approved golden image (`player-image-v*` Release) — see
   [`ops/players/image/`](../players/image/).
3. Generate a fresh config zip (Actions → **Kiosk config**, or
   `generate_kiosk_config.py`) using the **same** hostname fields (`location` /
   `unit`) and CMS URL/key; copy `kiosk.conf` to `/boot/firmware/`.
4. Prefer reusing the same hostname and DHCP reservation (update MAC in DHCP).
5. Boot; first-boot re-applies hostname and Arexibo env.
6. In CMS: decommission the old display if needed; authorize the new one into the
   **same display group**.
7. Confirm schedules apply automatically via the display group (no per-exhibit rebinding).
8. Verify with [`ops/scripts/bootstrap-check.sh`](../scripts/bootstrap-check.sh) and
   playback / reboot persistence.
9. Update private inventory (MAC address).
