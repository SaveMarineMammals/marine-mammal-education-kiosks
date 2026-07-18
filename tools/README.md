# Tools

CLI helpers to keep ~50 exhibits maintainable. **Python** is the chosen language for v1 tooling.

| Tool | Status | Purpose |
| --- | --- | --- |
| `serve_preview.py` | ready | Static server for branding/layout preview |
| `validate_exhibits.py` | stub | Schema-check exhibit.yaml, manifests, catalog |
| `sync_media.py` | stub | Push changed media-store objects into Xibo |
| `package_exhibit.py` | stub | Release checklist / optional export packaging |
| `catalog.py` | stub | Verify or regenerate `_catalog.yaml` |

Install deps with `pip install -r tools/requirements.txt` (`serve_preview.py` needs only the standard library).

For how to run these locally, see [docs/local-testing.md](../docs/local-testing.md).
