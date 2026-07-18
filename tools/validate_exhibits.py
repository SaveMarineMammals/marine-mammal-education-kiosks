#!/usr/bin/env python3
"""Validate exhibit packages against schemas and catalog consistency.

Usage:
  python tools/validate_exhibits.py
  python tools/validate_exhibits.py --exhibit humpback-migration
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXHIBITS = ROOT / "exhibits"
SCHEMAS = ROOT / "schemas"

try:
    import yaml
except ImportError:  # pragma: no cover - optional until deps are pinned
    yaml = None


def load_yaml(path: Path) -> dict:
    if yaml is None:
        print(
            "PyYAML is required: pip install pyyaml",
            file=sys.stderr,
        )
        sys.exit(2)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at document root")
    return data


def validate_structure(exhibit_dir: Path) -> list[str]:
    errors: list[str] = []
    required = [
        "exhibit.yaml",
        "README.md",
        "media/manifest.yaml",
    ]
    for rel in required:
        if not (exhibit_dir / rel).is_file():
            errors.append(f"missing {rel}")
    return errors


def validate_slug_match(exhibit_dir: Path, exhibit: dict, manifest: dict) -> list[str]:
    errors: list[str] = []
    slug = exhibit_dir.name
    if exhibit.get("slug") != slug:
        errors.append(f"exhibit.slug {exhibit.get('slug')!r} != folder {slug!r}")
    if manifest.get("exhibit") != slug:
        errors.append(f"manifest.exhibit {manifest.get('exhibit')!r} != folder {slug!r}")
    status = exhibit.get("status")
    if status not in {"draft", "review", "published", "retired"}:
        errors.append(f"invalid status {status!r}")
    return errors


def validate_catalog(catalog: dict, exhibit_dirs: list[Path]) -> list[str]:
    errors: list[str] = []
    entries = catalog.get("exhibits") or []
    by_slug = {e.get("slug"): e for e in entries if isinstance(e, dict)}
    for d in exhibit_dirs:
        if d.name not in by_slug:
            errors.append(f"catalog missing slug {d.name}")
            continue
        entry = by_slug[d.name]
        expected_path = f"exhibits/{d.name}"
        if entry.get("path") != expected_path:
            errors.append(f"catalog path for {d.name} should be {expected_path}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhibit", help="Validate a single slug")
    args = parser.parse_args()

    if not EXHIBITS.is_dir():
        print(f"exhibits directory not found: {EXHIBITS}", file=sys.stderr)
        return 1

    exhibit_dirs = sorted(
        p for p in EXHIBITS.iterdir() if p.is_dir() and not p.name.startswith("_")
    )
    if args.exhibit:
        exhibit_dirs = [EXHIBITS / args.exhibit]
        if not exhibit_dirs[0].is_dir():
            print(f"unknown exhibit: {args.exhibit}", file=sys.stderr)
            return 1

    all_errors: list[str] = []
    for exhibit_dir in exhibit_dirs:
        prefix = exhibit_dir.name
        struct_errors = validate_structure(exhibit_dir)
        all_errors.extend(f"{prefix}: {e}" for e in struct_errors)
        if struct_errors:
            continue
        try:
            exhibit = load_yaml(exhibit_dir / "exhibit.yaml")
            manifest = load_yaml(exhibit_dir / "media" / "manifest.yaml")
        except (ValueError, OSError) as exc:
            all_errors.append(f"{prefix}: {exc}")
            continue
        all_errors.extend(
            f"{prefix}: {e}" for e in validate_slug_match(exhibit_dir, exhibit, manifest)
        )

    catalog_path = EXHIBITS / "_catalog.yaml"
    if catalog_path.is_file() and yaml is not None:
        try:
            catalog = load_yaml(catalog_path)
            all_errors.extend(validate_catalog(catalog, exhibit_dirs if not args.exhibit else sorted(
                p for p in EXHIBITS.iterdir() if p.is_dir() and not p.name.startswith("_")
            )))
        except (ValueError, OSError) as exc:
            all_errors.append(f"catalog: {exc}")

    # Schemas are present for editor tooling; full jsonschema validation can be added
    # when jsonschema is pinned as a dependency.
    _ = SCHEMAS

    if all_errors:
        print("Validation failed:")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print(f"OK: {len(exhibit_dirs)} exhibit(s) passed structural validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
