# Tools

CLI helpers to keep ~50 exhibits maintainable. **Python** is the chosen language for v1 tooling.

| Tool | Status | Purpose |
| --- | --- | --- |
| `serve_preview.py` | ready | Static server for branding/layout preview |
| `validate_exhibits.py` | ready | Schema, media policy, timeline contract, catalog consistency |
| `catalog.py` | ready | Verify or regenerate `_catalog.yaml` |
| `sync_media.py` | ready | Push exhibit media into Xibo Library |
| `sync_cms.py` | ready | Published-only media + `mmek-<slug>` layout reconcile |
| `xibo_client.py` | ready | Production REST client (media/layouts; no schedules) |
| `xibo_layout.py` | ready | Timeline → stable layout upsert |
| `package_exhibit.py` | partial | Release checklist / optional export packaging |

Install deps with `pip install -r tools/requirements.txt` (`serve_preview.py` needs only the standard library).

CMS host deploy: [`ops/cms/scripts/deploy-cms-sync.sh`](../ops/cms/scripts/deploy-cms-sync.sh).

For how to run these locally, see [docs/local-testing.md](../docs/local-testing.md).

CI mirrors Tier 1 via `.github/workflows/exhibit-contract.yml`. Timeline stills use
`ops/qa/ci_timeline_preview.py` (see [docs/local-testing.md](../docs/local-testing.md)
Tier 2). Facility CMS sync uses `.github/workflows/cms-sync.yml` on a self-hosted
runner (see [ops/runbooks/cms-content-sync.md](../ops/runbooks/cms-content-sync.md)).
