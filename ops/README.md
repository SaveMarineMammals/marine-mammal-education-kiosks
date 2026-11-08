# Operations

Runbooks and conventions for Xibo CMS, Raspberry Pi players, networking, and media sync.

| Path | Purpose |
| --- | --- |
| [`cms/`](cms/) | CMS install notes, folder/tag taxonomy, credentials via env |
| [`players/`](players/) | Raspberry Pi bootstrap and Arexibo (community aarch64) |
| [`players/image/`](players/image/) | Golden Pi image recipe + kiosk config generator |
| [`qa/`](qa/) | Ephemeral Docker visual QA (CMS + headless player + captures); CI stills via `ci_timeline_preview.py` |
| [`networking/`](networking/) | Hostnames, DHCP, firewall assumptions |
| [`runbooks/`](runbooks/) | Publish, retire, replace a Pi, install CMS host, offline behavior |
| [`cms/scripts/`](cms/scripts/) | Ubuntu/Docker bootstrap + Xibo CMS install helpers |
| [`scripts/`](scripts/) | Shell helpers (`bootstrap-check.sh`, …) |

Facility panel mount and Pi BOM:
[`docs/facility-physical-setup.md`](../docs/facility-physical-setup.md).

## Common commands (repo root)

```bash
# Tier 1 / Tier 2 (developer machine)
python3 tools/validate_exhibits.py
python3 ops/qa/ci_timeline_preview.py --exhibit <slug>

# Per-kiosk first-boot config (local only — never via Actions)
# IMAGE_VERSION = recipe_version from the flashed image's build-info.txt
python3 ops/players/image/generate_kiosk_config.py \
  --location lobby --unit 01 \
  --cms-url https://cms.example.local \
  --cms-key "$CMS_KEY" \
  --image-version "$IMAGE_VERSION" \
  --out-dir /tmp/kiosk-configs

# Pi SSH smoke test
bash ops/scripts/bootstrap-check.sh kiosk-lobby-01
```

Download / flash golden images: [`players/README.md`](players/README.md).

GitHub Actions: **Exhibit contract** / **Timeline preview** (required on `main`);
**QA player capture** on demand or PRs labeled `qa-player`; **Player image** on
demand for fleet imaging. Details:
[docs/local-testing.md](../docs/local-testing.md),
[ops/players/image/](players/image/).
