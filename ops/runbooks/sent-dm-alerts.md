# Runbook: Sent.dm for MMEK admin SMS alerts

Configure [Sent.dm](https://docs.sent.dm/) so the **admin-alert** Lambda can SMS
operators on permanent CMS/player failures. Email uses Amazon SES in the same
Lambda (see [`security-patching.md`](security-patching.md)); Sent is SMS only.

Templates are **not** managed in Terraform (no official Sent provider). Create
them in the Sent dashboard (or API), then pass ids into Terraform tfvars.

## 1. Account and SMS channel

1. Create or sign in to a Sent organization at <https://app.sent.dm>.
2. Complete SMS sender / compliance steps Sent requires for your region.
3. Confirm you can send a test SMS from the dashboard.

## 2. Permanent-failure template

Create a **UTILITY** template named e.g. `mmek_permanent_failure` with variables
that match the Lambda payload parameters:

| Parameter | Meaning |
| --- | --- |
| `host` | Hostname (`cms-facility-01`, `kiosk-lobby-01`, …) |
| `role` | `cms` or `player` |
| `code` | Machine code (`cms_stack_update_failed`, `player_health_failed`, …) |
| `detail` | Short free-text detail (Lambda truncates for SMS) |

Example body (adapt to Sent’s template builder):

```text
MMEK alert: {{role}} {{host}} — {{code}}. {{detail}}
```

Submit for review if Sent requires it. Wait until status is **APPROVED** for SMS
before production alerts. Free-form `text` sends are **not** used for cold alerts;
always use this template.

Optional: create the template via API (`POST /v3/templates`) per
[Sent template definition](https://docs.sent.dm/reference/api/template-definition)
instead of the UI; still record the resulting id/name for Terraform.

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
sent_template_id     = "…"   # and/or sent_template_name = "mmek_permanent_failure"
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

Confirm SMS and email arrive. Check CloudWatch logs for
`mmek-production-admin-alert` (name prefix may vary).

## 7. Rotation checklist

- [ ] New Sent API key → Terraform apply
- [ ] New ingest token → Terraform apply + update CMS `alert.env` + regenerate
      player `kiosk.conf` / reflash or SCP `/etc/mmek/alert.env`
- [ ] Revoke old Sent key / old ingest token
- [ ] Re-run smoke test
