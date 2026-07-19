# Operations

Runbooks and conventions for Xibo CMS, Raspberry Pi players, networking, and media sync.

| Path | Purpose |
| --- | --- |
| [`cms/`](cms/) | CMS install notes, folder/tag taxonomy, credentials via env |
| [`players/`](players/) | Raspberry Pi bootstrap and Xibo Linux Player |
| [`qa/`](qa/) | Ephemeral Docker visual QA (CMS + headless player + captures); CI stills via `ci_timeline_preview.py` |
| [`networking/`](networking/) | Hostnames, DHCP, firewall assumptions |
| [`runbooks/`](runbooks/) | Publish, retire, replace a Pi, offline behavior |
| [`scripts/`](scripts/) | Shell helpers used by ops (thin wrappers around `tools/`) |

GitHub Actions: **Exhibit contract** / **Timeline preview** (required on `main`);
**QA player capture** on demand or PRs labeled `qa-player`. Details:
[docs/local-testing.md](../docs/local-testing.md).
