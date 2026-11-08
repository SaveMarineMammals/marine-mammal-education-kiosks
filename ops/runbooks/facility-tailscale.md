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
4. ACL tags and group (**required before** minting auth keys or running
   `install-tailscale.sh`). In the Tailscale admin console → **Access controls**,
   define the tags under `tagOwners`. Owners, Admins, and Network admins can
   apply any defined tag; the tags must still appear here or you get
   `requested tags […] are invalid or not permitted`.

```json
{
  "tagOwners": {
    "tag:mmek-cms": ["autogroup:admin"],
    "tag:mmek-players": ["autogroup:admin"]
  },
  "groups": {
    "group:mmek-admins": ["you@example.com"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["group:mmek-admins"],
      "dst": ["tag:mmek-cms:22", "tag:mmek-cms:443"]
    },
    {
      "action": "accept",
      "src": ["tag:mmek-players"],
      "dst": ["tag:mmek-cms:443", "tag:mmek-cms:9505"]
    }
  ]
}
```

Merge into your existing policy (do not wipe unrelated rules). Save/apply the
policy **before** creating keys.

| Identity | Role |
| --- | --- |
| `tag:mmek-cms` | CMS mini PC |
| `tag:mmek-players` | All kiosk Pis |
| `group:mmek-admins` | Operator users |

Optional later: allow `group:mmek-admins` → `tag:mmek-players:22` for Pi SSH.
Deny player↔player unless you add an explicit need.

5. Auth keys (never commit; treat like `CMS_KEY`):

| Key | Tags on the key | Use |
| --- | --- | --- |
| CMS join | **exactly** `tag:mmek-cms` | `TS_AUTHKEY` for `install-tailscale.sh` |
| Player join | **exactly** `tag:mmek-players` | `TS_AUTHKEY` in each `kiosk.conf` |

Create keys at **Settings → Keys → Generate auth key**:

1. Enable **Reusable** (or one-off for a single CMS join).
2. Enable **Pre-approved** if your tailnet requires device approval.
3. Under **Tags**, select **only** the matching tag (`tag:mmek-cms` or
   `tag:mmek-players`). Do not leave the key untagged and expect
   `--advertise-tags` to invent a tag — the key must carry that tag, and the
   tag must exist in `tagOwners`.
4. Copy the `tskey-auth-…` value once.

If join fails with `requested tags [tag:mmek-cms] are invalid or not permitted`:
the tag is missing from `tagOwners`, or the auth key was not created with that
tag. Fix the ACL, mint a **new** key, then re-run
`sudo … ./install-tailscale.sh` (add `--reset` via a one-off
`tailscale up --reset …` if a previous partial join left bad state).

Prefer **reusable, tag-only** keys with an expiry you rotate on a documented
schedule.

## 2. Split DNS (CMS hostname → Tailscale IP)

Tailscale split DNS only **forwards** queries for a domain to a nameserver; it
does not invent A records. Run dnsmasq on the CMS so that nameserver returns the
CMS `100.x` address.

1. Join the CMS first (§3) and note its Tailscale IPv4 (`tailscale ip -4`).
2. On the CMS, install the split-DNS nameserver:

   ```bash
   cd /path/to/marine-mammal-education-kiosks/ops/cms
   sudo ./scripts/install-cms-split-dns.sh
   ```

   That installs dnsmasq bound to `tailscale0`, answers
   `server.kiosks.local.belize.savemarinemammals.com` → this host's `100.x`, and
   opens UFW **53/udp+tcp** on `tailscale0`.

3. In the Tailscale admin console ([DNS](https://login.tailscale.com/admin/dns)):
   - Enable **MagicDNS**.
   - **Add nameserver** → **Custom** → CMS Tailscale IPv4.
   - Enable **Restrict to domain** →
     `kiosks.local.belize.savemarinemammals.com`.
   - Save.

4. Route 53 must keep a CMS **LAN** A record (e.g. `10.1.10.140`) for
   documentation/ACME context. Do **not** put `100.x` or a `*.ts.net` CNAME in
   Route 53 — public resolvers cannot follow MagicDNS names and Terraform
   expects an A record.
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
- Tightens UFW so **22 / 53 / 80 / 443 / 9505** are allowed on `tailscale0` and
  from `FACILITY_LAN_CIDR` only (writes `/etc/mmek/tailscale-ufw.lock` so
  `enable-cms-tls.sh` re-runs do not re-open ports to Anywhere)

Then finish split DNS (§2): `install-cms-split-dns.sh` + Tailscale admin
restricted nameserver.

## 4. Join kiosk players

1. Flash a golden image that includes the Tailscale package
   ([`../players/README.md`](../players/README.md)).
2. Generate `kiosk.conf` **locally** with a player auth key:

   ```bash
   export CMS_KEY='…'
   export TS_AUTHKEY='tskey-auth-…'   # tag:mmek-players only
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
   `tailscale up --advertise-tags=tag:mmek-players`, waits for a live tailnet,
   then starts Arexibo. `CMS_KEY` and `TS_AUTHKEY` are stripped from bootfs
   afterward (same pattern as before).

Pi replace: [`replace-pi.md`](replace-pi.md) — generate a fresh config with a
current `TS_AUTHKEY`; MagicDNS name matches `HOSTNAME`.

### Retrofit (already-booted Pi)

When first-boot already ran without Tailscale (or needs a re-join), copy
[`../players/scripts/join-tailscale.sh`](../players/scripts/join-tailscale.sh)
to the Pi and run it — do **not** put the auth key in Git or leave it on disk.

Some fleet images hold `arexibo` with apt-unsatisfiable Qt Depends (player still
runs). Plain `apt-get install tailscale` then fails; the script falls back to
`apt-get download` + `dpkg -i` for `iptables` + `tailscale` only.

```bash
# From a machine with the repo (or scp the script), then on the Pi:
export TS_AUTHKEY='tskey-auth-…'   # tag:mmek-players only; shell only
sudo -E ./join-tailscale.sh
unset TS_AUTHKEY
# Use TS_RESET=1 if a prior partial join left bad state.
tailscale ip -4
tailscale status
```

Then run the Pi checks in §5. Restart `arexibo.service` only if CMS reachability
was failing before the join.

## 5. Verify

On CMS:

```bash
tailscale status
tailscale ip -4
ufw status verbose
curl -fsSI https://server.kiosks.local.belize.savemarinemammals.com/login
```

On a Pi (or via SSH over Tailscale; Pi images may lack `dig`/`resolvectl`):

```bash
tailscale status
getent hosts server.kiosks.local.belize.savemarinemammals.com
# Expect the CMS 100.x address, not the facility LAN IP
tailscale ping kiosk-server   # or whatever TS_HOSTNAME the CMS used
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
| Rotate player auth keys | Mint a new `tag:mmek-players` key; use it on the next flash/`kiosk.conf`; revoke the old key in the admin console |

## References

- [`install-cms-host.md`](install-cms-host.md)
- [`../networking/README.md`](../networking/README.md)
- [`../cms/scripts/install-tailscale.sh`](../cms/scripts/install-tailscale.sh)
- [`../players/image/`](../players/image/)
- Tailscale ACL / auth keys: <https://tailscale.com/kb/1018/acls>
