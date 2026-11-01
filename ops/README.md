# Operations

Runbooks and conventions for Xibo CMS, Raspberry Pi players, networking, and media sync.

| Path | Purpose |
| --- | --- |
| [`cms/`](cms/) | CMS install notes, folder/tag taxonomy, credentials via env |
| [`players/`](players/) | Raspberry Pi bootstrap and Arexibo (community aarch64) |
| [`players/image/`](players/image/) | Golden Pi image recipe + kiosk config generator |
| [`qa/`](qa/) | Ephemeral Docker visual QA (CMS + headless player + captures); CI stills via `ci_timeline_preview.py` |
| [`networking/`](networking/) | Hostnames, DHCP, firewall assumptions |
| [`runbooks/`](runbooks/) | Publish, retire, replace a Pi, offline behavior |
| [`scripts/`](scripts/) | Shell helpers (`bootstrap-check.sh`, …) |

Facility panel mount and Pi BOM:
[`docs/facility-physical-setup.md`](../docs/facility-physical-setup.md).

GitHub Actions: **Exhibit contract** / **Timeline preview** (required on `main`);
**QA player capture** on demand or PRs labeled `qa-player`; **Player image** and
**Kiosk config** on demand for fleet imaging. Details:
[docs/local-testing.md](../docs/local-testing.md),
[ops/players/image/](players/image/).
