# Runbook: Sent.dm for MMEK admin SMS alerts

Configure [Sent.dm](https://docs.sent.dm/) so the **admin-alert** Lambda can SMS
operators on permanent CMS/player failures. Email uses Amazon SES in the same
Lambda (see [`security-patching.md`](security-patching.md)); Sent is SMS only.

Templates are **not** managed in Terraform (no official Sent provider). Use the
approved **`adm-siteerror`** template below (or recreate an equivalent if the
account differs).

## Why apply added 0 resources

The Lambda is created only when **all** of these are non-empty at apply time:

| Terraform variable | Typical source |
| --- | --- |
| `alert_ingest_token` | GitHub secret `MMEK_ALERT_INGEST_TOKEN` or `TF_VAR_alert_ingest_token` |
| `sent_api_key` | `MMEK_SENT_API_KEY` / `TF_VAR_sent_api_key` |
| `alert_sms_to` | `MMEK_ALERT_SMS_TO` / `TF_VAR_alert_sms_to` |
| `alert_email_to` | `MMEK_ALERT_EMAIL_TO` / `TF_VAR_alert_email_to` |
| `ses_from_email` | `MMEK_SES_FROM_EMAIL` / `TF_VAR_ses_from_email` |

`enable_admin_alert` defaults to **true**, but without those values Terraform
skips the module (DNS/ACME still apply → **0 added** for alerts). That is
intentional so facility DNS keeps working before Sent/SES are configured.

Committed [`terraform.tfvars`](../../infra/terraform/environments/production/terraform.tfvars)
does **not** hold secrets.

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
2. Store it only as a GitHub Environment secret or local `TF_VAR_*` — **never**
   commit it, and **never** put it on CMS hosts or Pis.
3. Rotate by issuing a new key, updating the secret, applying, then revoking the old key.

## 4. Wire into AWS (Terraform)

### Option A — GitHub Actions (preferred)

In the repo **Settings → Environments → `production` → Environment secrets**, add:

| Secret | Purpose |
| --- | --- |
| `MMEK_ALERT_INGEST_TOKEN` | Long random bearer shared with CMS/players |
| `MMEK_SENT_API_KEY` | Sent.dm `x-api-key` |
| `MMEK_ALERT_SMS_TO` | Comma-separated E.164 phones |
| `MMEK_ALERT_EMAIL_TO` | Comma-separated emails |
| `MMEK_SES_FROM_EMAIL` | Verified SES From address |

The GitHub OIDC role `mmek-terraform-ci` must allow Lambda/SES/Logs/IAM role
APIs for admin-alert. If apply fails with `AccessDenied` on `iam:CreateRole`,
`ses:VerifyEmailIdentity`, or `logs:CreateLogGroup`, re-apply bootstrap locally
([`infra/bootstrap/README.md`](../../infra/bootstrap/README.md)), then retry
Infrastructure Deployment.

Then run **Infrastructure Deployment** (`workflow_dispatch` on
[`.github/workflows/infra-cd.yml`](../../.github/workflows/infra-cd.yml)) or push
a change under `infra/**` to `main`. The workflow exports those as `TF_VAR_*`.

Generate an ingest token e.g.:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Option B — Local apply

```powershell
cd infra/terraform/environments/production
$env:TF_VAR_alert_ingest_token = "…"
$env:TF_VAR_sent_api_key = "…"
$env:TF_VAR_alert_sms_to = "+15551212"
$env:TF_VAR_alert_email_to = "ops@example.org"
$env:TF_VAR_ses_from_email = "alerts@example.org"
# then terraform-plan / terraform-apply helpers as usual
```

Optional overrides (template defaults already target `adm-siteerror`):

```hcl
# sent_template_id   = "5e3a2913-647a-408c-a3fe-d9cd3d103641"
# sent_template_name = "adm-siteerror"
# enable_admin_alert = false   # force skip even if TF_VAR_* are set
```

After a successful apply that creates the module:

```bash
terraform output -raw alert_lambda_url
```

Verify the SES From address in the SES console first. Terraform defaults to
`create_ses_alert_identity=false` (reference the verified address via
`MMEK_SES_FROM_EMAIL` only). Set that flag to `true` only if you want Terraform
to create/manage the identity. Exit the SES sandbox before sending to arbitrary
recipients.

Module details: [`infra/terraform/modules/admin-alert/`](../../infra/terraform/modules/admin-alert/).

## 5. Host clients

- CMS: `/etc/mmek/alert.env` from [`ops/cms/alert.env.example`](../cms/alert.env.example)
  (`ALERT_LAMBDA_URL`, `ALERT_INGEST_TOKEN` only — same token as
  `MMEK_ALERT_INGEST_TOKEN`).
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

- [ ] New Sent API key → update `MMEK_SENT_API_KEY` → Infrastructure Deployment
- [ ] New ingest token → update `MMEK_ALERT_INGEST_TOKEN` → apply + update CMS
      `alert.env` + regenerate player `kiosk.conf` / reflash or SCP
      `/etc/mmek/alert.env`
- [ ] Revoke old Sent key / old ingest token
- [ ] Re-run smoke test
