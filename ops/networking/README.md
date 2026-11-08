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

- **Tailscale overlay:** CMS host (`tag:mmek-cms`) and every kiosk Pi (`tag:mmek-player`)
  join the same tailnet. Players reach the CMS over Tailscale for **HTTPS 443**
  (XMDS / WebSocket XMR) and **9505** (classic XMR). Operators use the same
  overlay for SSH and the CMS UI. See
  [`../runbooks/facility-tailscale.md`](../runbooks/facility-tailscale.md).
- Facility **Ethernet** is the underlay (DHCP, internet, Tailscale direct/DERP)
  and a LAN break-glass path when the tailnet is down.
- Canonical CMS hostname:
  `server.kiosks.local.belize.savemarinemammals.com` (Let's Encrypt DNS-01 via
  Route 53 zone `kiosks.local.belize.savemarinemammals.com` + host Caddy — see
  [`../cms/caddy/README.md`](../cms/caddy/README.md) and
  [`../../infra/`](../../infra/)). Tailscale **split DNS** maps that name to the
  CMS Tailscale IPv4 for tailnet clients; do not put `100.x` addresses in Route 53.
- DHCP reservations for each Pi MAC address simplify replacement.
- Firewall (CMS UFW after Tailscale install): allow player → CMS on **443** and
  **9505** from `tailscale0` and the facility LAN CIDR; SSH similarly scoped.
  Public inbound **80** is not required for ACME (DNS-01).
- DNS zones (Terraform): `belize.savemarinemammals.com` →
  `kiosks.local.belize.savemarinemammals.com` (ACME TXT + CMS A/AAAA); parent
  `savemarinemammals.com` already exists.

## Inventory stub

Maintain a private inventory (not necessarily in Git) of MAC, hostname, location, and display group. A sanitized template:

| Hostname | Location | Display group | Notes |
| --- | --- | --- | --- |
| kiosk-lobby-01 | Lobby | lobby | |
