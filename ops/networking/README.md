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

- Players need reliable LAN/WAN access to the CMS (HTTPS preferred).
- DHCP reservations for each Pi MAC address simplify replacement.
- Firewall: allow player → CMS (XMDS/XMR as required by your Xibo version); block unnecessary inbound to Pis from the public internet.
- DNS: optional internal names for CMS (`cms.example.local`).

## Inventory stub

Maintain a private inventory (not necessarily in Git) of MAC, hostname, location, and display group. A sanitized template:

| Hostname | Location | Display group | Notes |
| --- | --- | --- | --- |
| kiosk-lobby-01 | Lobby | lobby | |
