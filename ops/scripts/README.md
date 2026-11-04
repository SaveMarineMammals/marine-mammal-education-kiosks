# Ops scripts

Thin wrappers around `tools/` and player helpers for common operator tasks.

| Script | Purpose |
| --- | --- |
| [`bootstrap-check.sh`](bootstrap-check.sh) | SSH smoke test (hostname, Arexibo unit, CMS_URL present) |
| [`../cms/scripts/`](../cms/scripts/) | CMS mini-PC bootstrap + Xibo Docker install |

Prefer implementing reusable logic under `tools/` or `ops/players/image/` and calling it from here.

Examples to add later:

- `sync-exhibit.sh <slug>`
- `validate-all.sh`
