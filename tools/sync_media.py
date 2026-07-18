#!/usr/bin/env python3
"""Sync exhibit media from the media store into Xibo CMS Library.

Stub: implements argument parsing and manifest loading. Wire CMS API + store
client when credentials and store endpoint are available.

Usage:
  python tools/sync_media.py --exhibit humpback-migration --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXHIBITS = ROOT / "exhibits"

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_manifest(slug: str) -> dict:
    path = EXHIBITS / slug / "media" / "manifest.yaml"
    if not path.is_file():
        raise FileNotFoundError(path)
    if yaml is None:
        raise RuntimeError("PyYAML is required: pip install pyyaml")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping")
    return data


def plan_uploads(manifest: dict) -> list[dict]:
    """Return assets that would be synced (all assets in stub mode)."""
    assets = manifest.get("assets") or []
    return [a for a in assets if isinstance(a, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhibit", required=True, help="Exhibit slug")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned uploads without contacting store or CMS",
    )
    args = parser.parse_args()

    try:
        manifest = load_manifest(args.exhibit)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    planned = plan_uploads(manifest)
    print(f"Exhibit: {args.exhibit}")
    print(f"Store: {manifest.get('store', '(unset)')}")
    print(f"Assets to sync: {len(planned)}")
    for asset in planned:
        print(
            f"  - {asset.get('id')}: {asset.get('uri')} "
            f"→ Library exhibits/{args.exhibit}/ ({asset.get('filename')})"
        )

    if args.dry_run:
        print("Dry run only; no uploads performed.")
        return 0

    print(
        "Live sync not implemented yet. Configure CMS/store clients and remove this stub.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
