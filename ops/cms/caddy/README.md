# Caddy TLS for Xibo CMS

Terminates HTTPS in front of `cms-web` with **Let's Encrypt DNS-01** against the
Route 53 zone **`kiosks.local.belize.savemarinemammals.com`** (created by
[`infra/`](../../../infra/)).

| File | Role |
| --- | --- |
| [`Caddyfile`](Caddyfile) | Site block + `tls { dns route53 { … } }` |
| [`caddy-acme.env.example`](caddy-acme.env.example) | AWS env vars → `/etc/mmek/caddy-acme.env` |
| [`route53-acme-iam-policy.json`](route53-acme-iam-policy.json) | Reference policy (prefer Terraform module `acme-route53-iam`) |

## Operator setup

1. Apply [`infra/terraform/environments/production`](../../../infra/terraform/environments/production/)
   (or wait for Infra apply CI).
2. On the CMS host:

   ```bash
   sudo mkdir -p /etc/mmek
   sudo cp ops/cms/caddy/caddy-acme.env.example /etc/mmek/caddy-acme.env
   sudo chmod 600 /etc/mmek/caddy-acme.env
   ```

3. Fill from Terraform outputs:

   | Env var | Output |
   | --- | --- |
   | `AWS_ACCESS_KEY_ID` | `acme_access_key_id` |
   | `AWS_SECRET_ACCESS_KEY` | `acme_secret_access_key` (sensitive) |
   | `AWS_REGION` | `us-east-1` |
   | `AWS_HOSTED_ZONE_ID` | `kiosks_zone_id` |

4. Keep the **A** record for `server.kiosks.local.belize.savemarinemammals.com`
   (set via `cms_server_ipv4` in production tfvars; LAN IP is fine).
5. Run [`../scripts/enable-cms-tls.sh`](../scripts/enable-cms-tls.sh).

`enable-cms-tls.sh` installs a Caddy binary built with
`github.com/caddy-dns/route53`. Renewal is automatic (TXT
`_acme-challenge.server` in the **kiosks** zone only).
