# Runbook: facility Tailscale (CMS + players)

Put the **CMS host** and every **kiosk Pi** on one Tailscale tailnet. XMDS
(HTTPS **443**) and classic XMR (**9505**) run over the overlay. Operators use
the same tailnet for SSH and the CMS UI. Facility Ethernet remains the underlay
(DHCP, internet, Tailscale direct/DERP) and a LAN break-glass path.

Canonical CMS hostname stays
`server.kiosks.local.belize.savemarinemammals.com` (Let's Encrypt via Caddy).
Do **not** put Tailscale IPs in Route 53. Do **not** enable subnet routers or
exit nodes on the CMS.

Companion script: [`../cms/scripts/install-tailscale.sh`](../cms/scripts/install-tailscale.sh).
Player first-boot join: [`../players/image/`](../players/image/).

## 1. Prereqs

1. Tailscale organization (admin access).
2. Facility LAN CIDR (e.g. `192.168.1.0/24`) for CMS UFW break-glass rules.
3. CMS reachable on the LAN (or physical console) for the first join.
4. ACL tags and group (create in the admin console before minting auth keys):

| Identity | Role |
| --- | --- |
| `tag:mmek-cms` | CMS mini PC |
| `tag:mmek-player` | All kiosk Pis |
| `group:mmek-admins` | Operator users |

Suggested ACL grants (edit to match your tailnet policy syntax):

- `group:mmek-admins` → `tag:mmek-cms`:22,443 (optional: SSH to `tag:mmek-player`)
- `tag:mmek-player` → `tag:mmek-cms`:443,9505
- Deny player↔player unless you add an explicit need later

5. Auth keys (never commit; treat like `CMS_KEY`):

| Key | Tags | Use |
| --- | --- | --- |
| CMS join | `tag:mmek-cms` only | `TS_AUTHKEY` for `install-tailscale.sh` |
| Player join | `tag:mmek-player` only | `TS_AUTHKEY` in each `kiosk.conf` |

Prefer **reusable, tag-only** keys with an expiry you rotate on a documented
schedule. Ephemeral one-off keys also work for a single CMS join.

## 2. Split DNS (CMS hostname → Tailscale IP)

1. Join the CMS first (§3) and note its Tailscale IPv4 (`tailscale ip -4`).
2. In the Tailscale admin console: enable **MagicDNS**.
3. Add **split DNS** (or an extra DNS record) so
   `server.kiosks.local.belize.savemarinemammals.com` resolves to that **100.x**
   address for every tailnet client (operators and Pis).

   Mapping the zone `kiosks.local.belize.savemarinemammals.com` is fine if your
   console only supports domain-level split DNS — ensure `server` still resolves
   to the CMS Tailscale IP (nameserver or override that returns the 100.x A
   record).

4. Route 53 may keep the CMS **LAN** A/AAAA for documentation/ACME context;
   Let's Encrypt DNS-01 does not need the A record to be the Tailscale IP.
5. Caddy already listens on host `:443` (all interfaces), including `tailscale0`.

Players keep
`CMS_URL=https://server.kiosks.local.belize.savemarinemammals.com` — only
resolution changes.

## 3. Join the CMS host

On the CMS (after [`install-cms-host.md`](install-cms-host.md) bootstrap; TLS may
be before or after Tailscale):

```bash
cd /path/to/marine-mammal-education-kiosks/ops/cms
chmod +x scripts/install-tailscale.sh
sudo FACILITY_LAN_CIDR=192.168.1.0/24 \
  TS_AUTHKEY='tskey-auth-…' \
  ./scripts/install-tailscale.sh
```

Omit `TS_AUTHKEY` for an interactive login URL. The script:

- Installs Tailscale and runs `tailscale up` with `--advertise-tags=tag:mmek-cms`
- Tightens UFW so **22 / 80 / 443 / 9505** are allowed on `tailscale0` and from
  `FACILITY_LAN_CIDR` only (writes `/etc/mmek/tailscale-ufw.lock` so
  `enable-cms-tls.sh` re-runs do not re-open ports to Anywhere)

Then finish split DNS (§2) with the CMS `100.x` address.

## 4. Join kiosk players

1. Flash a golden image that includes the Tailscale package
   ([`../players/README.md`](../players/README.md)).
2. Generate `kiosk.conf` **locally** with a player auth key:

   ```bash
   export CMS_KEY='…'
   export TS_AUTHKEY='tskey-auth-…'   # tag:mmek-player only
   python3 ops/players/image/generate_kiosk_config.py \
     --location lobby --unit 01 \
     --cms-url https://server.kiosks.local.belize.savemarinemammals.com \
     --cms-key "$CMS_KEY" \
     --ts-authkey "$TS_AUTHKEY" \
     --image-version "$IMAGE_VERSION" \
     --out-dir /tmp/kiosk-configs
   ```

3. Copy `kiosk.conf` to the SD boot volume; power on.
4. First-boot sets the hostname, runs
   `tailscale up --advertise-tags=tag:mmek-player`, waits for a live tailnet,
   then starts Arexibo. `CMS_KEY` and `TS_AUTHKEY` are stripped from bootfs
   afterward (same pattern as before).

Pi replace: [`replace-pi.md`](replace-pi.md) — generate a fresh config with a
current `TS_AUTHKEY`; MagicDNS name matches `HOSTNAME`.

## 5. Verify

On CMS:

```bash
tailscale status
tailscale ip -4
ufw status verbose
curl -fsSI https://server.kiosks.local.belize.savemarinemammals.com/login
```

On a Pi (or via SSH over Tailscale):

```bash
tailscale status
getent hosts server.kiosks.local.belize.savemarinemammals.com
# Expect the CMS 100.x address, not only the LAN IP
tailscale ping cms-facility-01   # or whatever TS_HOSTNAME the CMS used
systemctl is-active arexibo.service
```

In Xibo CMS → Displays: player authorized; XMR connected. From an operator
laptop on the tailnet: SSH to the CMS MagicDNS name and open the HTTPS CMS URL.

## 6. Break-glass

| Situation | Action |
| --- | --- |
| Tailscale down, on-site | Use facility LAN IP/SSH; UFW still allows `FACILITY_LAN_CIDR` for 22/443/9505 |
| Need temporary world-open SSH | Console/LAN: `sudo ufw allow OpenSSH`, fix Tailscale, then re-run `install-tailscale.sh` with `TIGHTEN_UFW=1` |
| Remove lockdown marker | Delete `/etc/mmek/tailscale-ufw.lock` only if you intentionally want `enable-cms-tls.sh` to restore Anywhere allows |
| Rotate player auth keys | Mint a new `tag:mmek-player` key; use it on the next flash/`kiosk.conf`; revoke the old key in the admin console |

## References

- [`install-cms-host.md`](install-cms-host.md)
- [`../networking/README.md`](../networking/README.md)
- [`../cms/scripts/install-tailscale.sh`](../cms/scripts/install-tailscale.sh)
- [`../players/image/`](../players/image/)
- Tailscale ACL / auth keys: <https://tailscale.com/kb/1018/acls>
