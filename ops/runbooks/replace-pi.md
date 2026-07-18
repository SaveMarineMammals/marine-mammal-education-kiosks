# Runbook: replace a failed Raspberry Pi

1. Note the failed unit’s hostname, display group, and CMS display name.
2. Provision a new Pi per [`ops/players/README.md`](../players/README.md).
3. Prefer reusing the same hostname and DHCP reservation (update MAC in DHCP).
4. Install Xibo Linux Player; connect to CMS.
5. In CMS: decommission the old display if needed; authorize the new one into the **same display group**.
6. Confirm schedules apply automatically via the display group (no per-exhibit rebinding).
7. Verify playback and reboot persistence.
8. Update private inventory (MAC address).
