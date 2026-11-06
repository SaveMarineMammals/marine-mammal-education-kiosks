#!/usr/bin/env python3
"""Generate per-kiosk first-boot configuration artifacts.

Used by GitHub Actions (kiosk-config.yml) and local operators.
Does not print CMS_KEY to stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path

LOCATION_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
UNIT_RE = re.compile(r"^\d{1,3}$")


def _pad_unit(unit: str) -> str:
    n = int(unit)
    if n < 0 or n > 999:
        raise ValueError("unit must be 0–999")
    return f"{n:02d}" if n < 100 else f"{n:03d}"


def _hostname(location: str, unit: str) -> str:
    if not LOCATION_RE.match(location):
        raise ValueError(
            f"invalid location {location!r}: use kebab-case ASCII (e.g. lobby, classroom-a)"
        )
    padded = _pad_unit(unit)
    if not UNIT_RE.match(unit.strip()) and not padded:
        raise ValueError(f"invalid unit {unit!r}")
    return f"kiosk-{location}-{padded}"


def _validate_cms_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not (url.startswith("https://") or url.startswith("http://")):
        raise ValueError("cms_url must start with https:// or http://")
    return url


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def generate(
    *,
    location: str,
    unit: str,
    cms_url: str,
    cms_key: str,
    display_group: str | None,
    image_version: str,
    out_dir: Path,
) -> Path:
    if not cms_key.strip():
        raise ValueError("cms_key must be non-empty")

    host = _hostname(location.strip().lower(), unit.strip())
    url = _validate_cms_url(cms_url)
    group = (display_group or location).strip().lower()
    if not LOCATION_RE.match(group):
        raise ValueError(f"invalid display_group {group!r}")

    bundle = out_dir / host
    bundle.mkdir(parents=True, exist_ok=True)

    kiosk_conf = bundle / "kiosk.conf"
    kiosk_conf.write_text(
        "\n".join(
            [
                f"HOSTNAME={host}",
                f"CMS_URL={url}",
                f"CMS_KEY={cms_key.strip()}",
                f"DISPLAY_GROUP={group}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    inventory = bundle / "inventory.env"
    inventory.write_text(
        "\n".join(
            [
                f"HOSTNAME={host}",
                f"CMS_URL={url}",
                f"DISPLAY_GROUP={group}",
                f"IMAGE_VERSION={image_version}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    deploy = bundle / "DEPLOY.md"
    deploy.write_text(
        "\n".join(
            [
                f"# Deploy {host}",
                "",
                "## 1. Flash golden image",
                "",
                f"- Use approved Release **player-image-v{image_version}** "
                f"(or matching soak artifact) from the `player-image` workflow.",
                "- Flash the `.img.xz` to the SD card (Raspberry Pi Imager / `xzcat | dd`).",
                "",
                "## 2. Copy first-boot config",
                "",
                "Mount the boot partition and copy this folder's `kiosk.conf` to:",
                "",
                "```text",
                "/boot/firmware/kiosk.conf",
                "```",
                "",
                "## 3. Network",
                "",
                f"- Create a DHCP reservation for this Pi's MAC → hostname `{host}`.",
                "",
                "## 4. Power on and authorize",
                "",
                "1. Boot the kiosk; first-boot applies hostname and Arexibo env.",
                "2. In Xibo CMS → Displays: authorize the new display.",
                f"3. Assign display group **`{group}`** (location/role, not exhibit name).",
                "4. Set display profile to **1920×1080** landscape.",
                "",
                "## Authentication note",
                "",
                "Players authenticate to XMDS with the shared **CMS Key** (in `kiosk.conf`) "
                "plus a per-display hardware key. Client certificates cannot replace the CMS key.",
                "",
                "## 5. Verify",
                "",
                "```bash",
                f"ops/scripts/bootstrap-check.sh {host}",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Checksums for non-secret files only (kiosk.conf contains CMS_KEY — hash still OK for integrity)
    sums = bundle / "sha256sums.txt"
    lines = []
    for name in ("kiosk.conf", "inventory.env", "DEPLOY.md"):
        p = bundle / name
        lines.append(f"{_sha256_file(p)}  {name}")
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")

    zip_path = out_dir / f"{host}-config.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in bundle.iterdir():
            if path.is_file():
                zf.write(path, arcname=f"{host}/{path.name}")

    return zip_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--location", required=True, help="kebab-case location (e.g. lobby)")
    parser.add_argument("--unit", required=True, help="unit number (e.g. 01)")
    parser.add_argument("--cms-url", required=True, help="Xibo CMS base URL")
    parser.add_argument("--cms-key", required=True, help="Xibo CMS key (not printed)")
    parser.add_argument(
        "--display-group",
        default="",
        help="Xibo display group (default: same as location)",
    )
    parser.add_argument(
        "--image-version",
        default="1.0.0",
        help="Golden image recipe version to reference in DEPLOY.md",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("kiosk-configs"),
        help="Output directory for bundle + zip",
    )
    args = parser.parse_args(argv)

    try:
        zip_path = generate(
            location=args.location,
            unit=args.unit,
            cms_url=args.cms_url,
            cms_key=args.cms_key,
            display_group=args.display_group or None,
            image_version=args.image_version.strip() or "1.0.0",
            out_dir=args.out_dir,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Never print cms_key; only paths.
    print(f"wrote {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
