#!/usr/bin/env python3
"""Assemble a release checklist for an exhibit package.

Usage:
  python tools/package_exhibit.py --exhibit humpback-migration
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXHIBITS = ROOT / "exhibits"
DIST = ROOT / "dist"

CHECKLIST = [
    "exhibit.yaml status is review or published",
    "media/manifest.yaml hashes match in-repo assets or media-store objects",
    "Library folder exhibits/<slug> populated in CMS",
    "Layout built from framework template and previewed",
    "schedule/intent.yaml reflected in CMS schedules",
    "catalog entry updated",
    "No files ≥ 2 MB (or video) committed under exhibits/ — those use the media store",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhibit", required=True)
    args = parser.parse_args()

    exhibit_dir = EXHIBITS / args.exhibit
    if not exhibit_dir.is_dir():
        print(f"unknown exhibit: {args.exhibit}", file=sys.stderr)
        return 1

    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"{args.exhibit}-checklist.txt"
    lines = [
        f"Package checklist: {args.exhibit}",
        f"Source: {exhibit_dir.relative_to(ROOT)}",
        "",
        "Do not write media-heavy Xibo export ZIPs into Git.",
        f"If you export a layout ZIP for transfer, place it under {DIST}/ (gitignored).",
        "",
        "Checklist:",
    ]
    lines.extend(f"  [ ] {item}" for item in CHECKLIST)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
