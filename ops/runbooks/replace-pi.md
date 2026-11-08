# Runbook: replace a failed Raspberry Pi

1. Note the failed unit’s hostname, display group, CMS display name, and MAC.
2. Flash the same approved golden image (`player-image-v*` Release) — download,
   verify, and flash steps: [`ops/players/README.md`](../players/README.md).
3. Generate a fresh config zip **locally** (never via GitHub Actions) using the
   **same** hostname fields (`location` / `unit`) and CMS URL/key:

   ```bash
   export CMS_KEY='…'        # do not commit
   export TS_AUTHKEY='…'     # tag:mmek-players; do not commit
   # IMAGE_VERSION = recipe_version from the flashed image's build-info.txt
   python3 ops/players/image/generate_kiosk_config.py \
     --location lobby --unit 01 \
     --cms-url https://server.kiosks.local.belize.savemarinemammals.com \
     --cms-key "$CMS_KEY" \
     --ts-authkey "$TS_AUTHKEY" \
     --image-version "$IMAGE_VERSION" \
     --out-dir /tmp/kiosk-configs
   ```

   Copy `kiosk.conf` from the zip bundle to the SD boot partition as `kiosk.conf`.
4. Prefer reusing the same hostname and DHCP reservation (update MAC in DHCP).
   MagicDNS name matches `HOSTNAME`; remove or disable the old Pi’s Tailscale
   node in the admin console if it still appears online.
5. Boot; first-boot re-applies hostname, joins Tailscale, and writes Arexibo env.
6. In CMS: decommission the old display if needed; authorize the new one into the
   **same display group**.
7. Confirm schedules apply automatically via the display group (no per-exhibit rebinding).
8. Verify playback / reboot persistence, then smoke-test over SSH:

   ```bash
   bash ops/scripts/bootstrap-check.sh kiosk-lobby-01
   # or: bash ops/scripts/bootstrap-check.sh <ip> mmek
   ```

9. Update private inventory (MAC address).
