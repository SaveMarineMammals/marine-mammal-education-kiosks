# Runbook: Sent.dm for MMEK admin SMS alerts

Configure [Sent.dm](https://docs.sent.dm/) so the **admin-alert** Lambda can SMS
operators on permanent CMS/player failures. Email uses Amazon SES in the same
Lambda (see [`security-patching.md`](security-patching.md)); Sent is SMS only.

Templates are **not** managed in Terraform (no official Sent provider). Use the
approved **`adm-siteerror`** template below (or recreate an equivalent if the
account differs).

## 1. Account and SMS channel

1. Create or sign in to a Sent organization at <https://app.sent.dm>.
2. Complete SMS sender / compliance steps Sent requires for your region.
3. Confirm you can send a test SMS from the dashboard.

## 2. Template: `adm-siteerror`

**Default template id:** `5e3a2913-647a-408c-a3fe-d9cd3d103641`  
**Name:** `adm-siteerror`

Sent templates **must not end with a variable**. Approved body:

```text
There has been a site error that requires your attention.
Site: {{site}}
Detail: {{detail}}
Review run books in GitHub.
```

| Parameter | Filled by Lambda |
| --- | --- |
| `site` | `{role}:{host}` (e.g. `cms:cms-facility-01`, `player:kiosk-lobby-01`) |
| `detail` | `{code}: {detail}` from the host alert (truncated for SMS) |

Confirm status is **APPROVED** for SMS before production alerts. Free-form
`text` sends are **not** used for cold alerts; always use this template.

If you recreate the template in another Sent org, update Terraform
`sent_template_id` / `sent_template_name` to match. Keep the same variable names
and keep a fixed sentence **after** `{{detail}}`.

## 3. API key

1. Create a Customer **API key** in Sent.
2. Store it only as Terraform sensitive input `sent_api_key` (local `tfvars` or
   GitHub Environment secret consumed by infra apply) — **never** commit it, and
   **never** put it on CMS hosts or Pis.
3. Rotate by issuing a new key, updating Terraform, applying, then revoking the old key.

## 4. Wire into AWS (Terraform)

In [`infra/terraform/environments/production/`](../../infra/terraform/environments/production/):

```hcl
enable_admin_alert   = true
alert_ingest_token   = "…"   # long random bearer shared with hosts
sent_api_key         = "…"
# Defaults already point at adm-siteerror; override only if the id differs:
# sent_template_id   = "5e3a2913-647a-408c-a3fe-d9cd3d103641"
# sent_template_name = "adm-siteerror"
alert_sms_to         = "+15551212,+15553434"
alert_email_to       = "ops@example.org"
ses_from_email       = "alerts@example.org"
```

Apply (CI on `main` or local). Then:

```bash
terraform output -raw alert_lambda_url
```

Verify the SES From address (click the verification email if
`create_ses_alert_identity=true`). Exit the SES sandbox before sending to
arbitrary recipients.

Module details: [`infra/terraform/modules/admin-alert/`](../../infra/terraform/modules/admin-alert/).

## 5. Host clients

- CMS: `/etc/mmek/alert.env` from [`ops/cms/alert.env.example`](../cms/alert.env.example)
  (`ALERT_LAMBDA_URL`, `ALERT_INGEST_TOKEN` only).
- Players: optional `ALERT_*` in `kiosk.conf` via
  [`generate_kiosk_config.py`](../players/image/generate_kiosk_config.py)
  (`--alert-lambda-url` / `--alert-ingest-token`).

Hosts never receive the Sent API key.

## 6. Smoke test

```bash
# From a configured CMS host (or any machine with the env file):
sudo /usr/local/sbin/mmek-admin-alert test_alert "Sent.dm + SES smoke"
# Clear dedup if re-testing the same code:
sudo rm -f /var/lib/mmek/alert-sent/test_alert
```

Expected SMS shape:

```text
There has been a site error that requires your attention.
Site: cms:…
Detail: test_alert: Sent.dm + SES smoke
Review run books in GitHub.
```

Confirm SMS and email arrive. Check CloudWatch logs for
`mmek-production-admin-alert` (name prefix may vary).

## 7. Rotation checklist

- [ ] New Sent API key → Terraform apply
- [ ] New ingest token → Terraform apply + update CMS `alert.env` + regenerate
      player `kiosk.conf` / reflash or SCP `/etc/mmek/alert.env`
- [ ] Revoke old Sent key / old ingest token
- [ ] Re-run smoke test
