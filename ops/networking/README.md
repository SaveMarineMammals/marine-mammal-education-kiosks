# Networking

## Hostname scheme

```text
kiosk-<location>-<nn>
```

Examples: `kiosk-lobby-01`, `kiosk-classroom-a-02`.

## Display groups vs hosts

- **Display groups** in Xibo are named by location/role (`lobby`, `classroom-a`).
- Individual players keep unique hostnames; CMS display names should match hostnames for supportability.

## Assumptions

- Players need reliable LAN access to the CMS over **HTTPS**.
- Canonical CMS hostname:
  `server.kiosks.local.belize.savemarinemammals.com` (Let's Encrypt DNS-01 via
  Route 53 zone `kiosks.local.belize.savemarinemammals.com` + host Caddy — see
  [`../cms/caddy/README.md`](../cms/caddy/README.md) and
  [`../../infra/`](../../infra/)).
- DHCP reservations for each Pi MAC address simplify replacement.
- Firewall: allow player → CMS on **443** (XMDS / WebSocket XMR) and **9505**
  (classic XMR); block unnecessary inbound to Pis from the public internet.
  Public inbound **80** is not required for ACME (DNS-01).
- DNS zones (Terraform): `belize.savemarinemammals.com` →
  `kiosks.local.belize.savemarinemammals.com` (ACME TXT + CMS A/AAAA); parent
  `savemarinemammals.com` already exists.

## Inventory stub

Maintain a private inventory (not necessarily in Git) of MAC, hostname, location, and display group. A sanitized template:

| Hostname | Location | Display group | Notes |
| --- | --- | --- | --- |
| kiosk-lobby-01 | Lobby | lobby | |
