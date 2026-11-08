# Module: acme-route53-iam

IAM user with least-privilege Route 53 rights on a single hosted zone for Caddy
Let's Encrypt **DNS-01**. Optionally creates an access key (secret in state).

Wire outputs into `/etc/mmek/caddy-acme.env` on the CMS host:

```text
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_HOSTED_ZONE_ID=<kiosks zone id>
```
