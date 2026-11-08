# admin-alert

AWS Lambda that accepts permanent-failure POSTs from CMS/players and sends:

- **Email** via Amazon SES
- **SMS** via [Sent.dm](https://docs.sent.dm/) (`POST /v3/messages`, SMS channel)

## Auth

Function URL uses `authorization_type = NONE`. The handler requires
`Authorization: Bearer <ALERT_INGEST_TOKEN>`.

## Host config

After apply:

```bash
terraform output -raw alert_lambda_url
```

Put URL + ingest token in `/etc/mmek/alert.env` (see `ops/cms/alert.env.example`).
Sent API key and recipient lists stay in Lambda env only.

## Prerequisites

1. Follow [`ops/runbooks/sent-dm-alerts.md`](../../../../ops/runbooks/sent-dm-alerts.md).
2. Verify SES From address (module can create `aws_ses_email_identity`; click the
   verification email). Exit SES sandbox before production sends to arbitrary To:
   addresses.
3. Set production tfvars / GitHub Environment secrets (see environment README).
