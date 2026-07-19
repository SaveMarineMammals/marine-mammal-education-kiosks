#!/usr/bin/env python3
"""Validate exhibit packages against schemas, media policy, and timeline contracts.

Usage:
  python tools/validate_exhibits.py
  python tools/validate_exhibits.py --exhibit humpback-migration
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXHIBITS = ROOT / "exhibits"
FRAMEWORK = ROOT / "framework"
SCHEMAS = ROOT / "schemas"

MAX_IN_REPO_BYTES = 2 * 1024 * 1024
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}
FORBIDDEN_MASTER_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v"}

GLANCE_AND_MATCH_REGIONS = (
    "insights-bg",
    "hero-bg",
    "hero-still",
    "hero-labels",
    "insights-art",
    "insights-copy",
    "ticker",
)

# Markdown / rich-text markers that break Xibo plain-text widgets.
MARKDOWN_PATTERNS = (
    re.compile(r"\*\*[^*]+\*\*"),
    re.compile(r"__[^_]+__"),
    re.compile(r"`[^`]+`"),
    re.compile(r"^\s*#{1,6}\s", re.MULTILINE),
    re.compile(r"\[.+\]\(.+\)"),
)
FANCY_BULLET_CHARS = "•·●○▪▸►◆◇★☆"
# Rough emoji / non-ASCII symbol ranges commonly pasted into copy.
NON_ASCII_SYMBOL = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]"
)

# High-confidence credential patterns only (avoid flagging docs / QA bootstrap code).
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-(?:live|test)-[A-Za-z0-9]{20,}\b"),
    re.compile(
        r"(?i)\b(?:aws)?_?(?:secret)?_?access_?key(?:_id)?\s*[:=]\s*['\"][A-Za-z0-9/+=]{20,}['\"]"
    ),
)

SECRET_SCAN_GLOBS = (
    "**/*.py",
    "**/*.yml",
    "**/*.yaml",
    "**/*.json",
    "**/*.md",
    "**/*.env",
    "**/*.sh",
    "**/*.ps1",
    "**/*.txt",
)
SECRET_SCAN_SKIP_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "artifacts",
    "dist",
    "media",  # binary-heavy; secrets belong in text configs
}
SECRET_SCAN_SKIP_NAMES = {
    ".env.example",
    "config.env.example",
}

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    jsonschema = None
    Draft202012Validator = None  # type: ignore[misc, assignment]


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        print("PyYAML is required: pip install -r tools/requirements.txt", file=sys.stderr)
        sys.exit(2)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at document root")
    return data


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMAS / name
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_against_schema(data: dict[str, Any], schema_name: str, label: str) -> list[str]:
    if jsonschema is None or Draft202012Validator is None:
        print(
            "jsonschema is required: pip install -r tools/requirements.txt",
            file=sys.stderr,
        )
        sys.exit(2)
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{label} schema ({schema_name}): {path}: {err.message}")
    return errors


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


def validate_slug_match(exhibit_dir: Path, exhibit: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
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


def validate_catalog(catalog: dict[str, Any], exhibit_dirs: list[Path]) -> list[str]:
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


def is_git_lfs_pointer(path: Path) -> bool:
    """True when the working tree file is an unresolved Git LFS pointer stub."""
    try:
        if path.stat().st_size > 1024:
            return False
        head = path.read_bytes()[:120]
    except OSError:
        return False
    return head.startswith(b"version https://git-lfs.github.com/spec/")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_repo_relative_uri(uri: str) -> bool:
    if not uri or uri.startswith(("http://", "https://", "s3://")):
        return False
    if uri.startswith("sha256/"):
        return False
    return not Path(uri).is_absolute()


def validate_manifest_assets(exhibit_dir: Path, manifest: dict[str, Any]) -> list[str]:
    """Verify in-repo media policy: size, hashes, and no video masters in Git."""
    errors: list[str] = []
    assets = manifest.get("assets") or []
    if not isinstance(assets, list):
        return ["manifest.assets must be a list"]

    for asset in assets:
        if not isinstance(asset, dict):
            errors.append("manifest asset entry must be a mapping")
            continue
        asset_id = asset.get("id") or "(unknown)"
        uri = str(asset.get("uri") or "").strip()
        if not is_repo_relative_uri(uri):
            # External media-store objects are not verified on disk here.
            continue

        path = ROOT / uri
        if not path.is_file():
            errors.append(f"asset {asset_id}: missing file for uri {uri}")
            continue

        if is_git_lfs_pointer(path):
            errors.append(
                f"asset {asset_id}: {uri} is a Git LFS pointer (run "
                "`git lfs pull`, or enable `lfs: true` on Actions checkout)"
            )
            continue

        size = path.stat().st_size
        if size >= MAX_IN_REPO_BYTES:
            errors.append(
                f"asset {asset_id}: {uri} is {size} bytes (>= 2 MB); use the media store"
            )
        if path.suffix.lower() in FORBIDDEN_MASTER_SUFFIXES:
            errors.append(f"asset {asset_id}: video file {uri} must not be committed to Git")

        expected_sha = str(asset.get("sha256") or "").strip().lower()
        if expected_sha:
            actual = file_sha256(path)
            if actual != expected_sha:
                errors.append(
                    f"asset {asset_id}: sha256 mismatch for {uri} "
                    f"(manifest {expected_sha[:12]}… != file {actual[:12]}…)"
                )

        expected_bytes = asset.get("bytes")
        if expected_bytes is not None and int(expected_bytes) != size:
            errors.append(
                f"asset {asset_id}: bytes mismatch for {uri} "
                f"(manifest {expected_bytes} != file {size})"
            )

        mime = str(asset.get("mime") or "").lower()
        if mime.startswith("video/"):
            errors.append(f"asset {asset_id}: video mime {mime} must use the media store")

    return errors


def iter_binary_candidates(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    files: list[Path] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        # Skip docs/readme text under media folders.
        if path.suffix.lower() in {".md", ".txt", ".yaml", ".yml", ".json"}:
            continue
        files.append(path)
    return files


def validate_tree_media_policy() -> list[str]:
    """Reject oversized or video binaries under exhibits/*/media and framework/."""
    errors: list[str] = []
    roots: list[Path] = []
    if EXHIBITS.is_dir():
        for exhibit_dir in EXHIBITS.iterdir():
            if exhibit_dir.is_dir() and not exhibit_dir.name.startswith("_"):
                media = exhibit_dir / "media"
                if media.is_dir():
                    roots.append(media)
    if FRAMEWORK.is_dir():
        roots.append(FRAMEWORK)

    for root in roots:
        for path in iter_binary_candidates(root):
            rel = path.relative_to(ROOT).as_posix()
            size = path.stat().st_size
            suffix = path.suffix.lower()
            if suffix in VIDEO_SUFFIXES:
                errors.append(f"media policy: video committed at {rel}")
            elif size >= MAX_IN_REPO_BYTES:
                errors.append(f"media policy: {rel} is {size} bytes (>= 2 MB)")
            elif suffix == ".zip" and size >= MAX_IN_REPO_BYTES:
                errors.append(f"media policy: large zip at {rel} (>= 2 MB)")
    return errors


def copy_is_cms_safe(text: str) -> list[str]:
    problems: list[str] = []
    if any(ch in text for ch in FANCY_BULLET_CHARS):
        problems.append("contains fancy bullet characters (use ASCII '-')")
    if NON_ASCII_SYMBOL.search(text):
        problems.append("contains emoji or symbol glyphs")
    for pattern in MARKDOWN_PATTERNS:
        if pattern.search(text):
            problems.append("contains Markdown markup (timeline copy must be plain text)")
            break
    # Allow common Latin-1 accented letters in species names; flag other high codepoints lightly.
    return problems


def validate_timeline(
    exhibit_dir: Path,
    exhibit: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    timeline_path = exhibit_dir / "layouts" / "timeline.yaml"
    if not timeline_path.is_file():
        # Timelines are expected for Glance & Match / layered stills packages.
        layout_template = str(exhibit.get("layoutTemplate") or "")
        if layout_template in {"glance-and-match", "layered-stills-loop"}:
            errors.append("missing layouts/timeline.yaml")
        return errors

    try:
        timeline = load_yaml(timeline_path)
    except (ValueError, OSError) as exc:
        return [f"timeline: {exc}"]

    template = str(timeline.get("template") or exhibit.get("layoutTemplate") or "").strip()
    regions = timeline.get("regions")
    if not isinstance(regions, dict) or not regions:
        errors.append("timeline.regions must be a non-empty mapping")
        return errors

    if template == "glance-and-match" or exhibit.get("layoutTemplate") == "glance-and-match":
        missing = [name for name in GLANCE_AND_MATCH_REGIONS if name not in regions]
        if missing:
            errors.append(
                "glance-and-match missing region(s): " + ", ".join(missing)
            )
        # Reject inventing background/midground for this template.
        forbidden = {"background", "midground"} & set(regions)
        if forbidden:
            errors.append(
                "glance-and-match must not use region(s): " + ", ".join(sorted(forbidden))
            )

    asset_ids = {
        str(a.get("id"))
        for a in (manifest.get("assets") or [])
        if isinstance(a, dict) and a.get("id")
    }

    ticker_has_scroll = False
    for region_name, region in regions.items():
        if not isinstance(region, dict):
            errors.append(f"timeline region {region_name!r} must be a mapping")
            continue
        widgets = region.get("widgets") or []
        if not isinstance(widgets, list):
            errors.append(f"timeline region {region_name!r} widgets must be a list")
            continue
        for widget in widgets:
            if not isinstance(widget, dict):
                continue
            wid = widget.get("id") or "(widget)"
            asset_ref = widget.get("asset")
            if asset_ref and str(asset_ref) not in asset_ids:
                errors.append(
                    f"timeline widget {wid}: asset {asset_ref!r} not in media manifest"
                )
            effect = str(widget.get("effect") or "").strip()
            if region_name == "ticker" and effect == "tickerScroll":
                ticker_has_scroll = True
            if effect.lower() in {"cssmarquee", "htmlmarquee", "keyframes"}:
                errors.append(
                    f"timeline widget {wid}: effect {effect!r} is not allowed; "
                    "use tickerScroll (maps to Xibo marqueeLeft)"
                )
            copy = widget.get("copy")
            if copy is not None:
                if not isinstance(copy, str):
                    errors.append(f"timeline widget {wid}: copy must be a string")
                else:
                    for problem in copy_is_cms_safe(copy):
                        errors.append(f"timeline widget {wid}: {problem}")

    if template == "glance-and-match" or exhibit.get("layoutTemplate") == "glance-and-match":
        if "ticker" in regions and not ticker_has_scroll:
            errors.append(
                "glance-and-match ticker must use effect: tickerScroll "
                "(native Xibo marqueeLeft)"
            )

    return errors


def validate_secrets() -> list[str]:
    errors: list[str] = []
    for pattern in SECRET_SCAN_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            if any(part in SECRET_SCAN_SKIP_PARTS for part in path.parts):
                continue
            if path.name.endswith(".example") or path.name in SECRET_SCAN_SKIP_NAMES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for secret_re in SECRET_PATTERNS:
                if secret_re.search(text):
                    rel = path.relative_to(ROOT).as_posix()
                    errors.append(f"possible secret in {rel}")
                    break
    return errors


def list_exhibit_dirs(only: str | None) -> list[Path]:
    if not EXHIBITS.is_dir():
        return []
    dirs = sorted(
        p for p in EXHIBITS.iterdir() if p.is_dir() and not p.name.startswith("_")
    )
    if only:
        target = EXHIBITS / only
        if not target.is_dir():
            return []
        return [target]
    return dirs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhibit", help="Validate a single slug")
    parser.add_argument(
        "--skip-secrets",
        action="store_true",
        help="Skip repo-wide secret pattern scan",
    )
    args = parser.parse_args()

    if not EXHIBITS.is_dir():
        print(f"exhibits directory not found: {EXHIBITS}", file=sys.stderr)
        return 1

    exhibit_dirs = list_exhibit_dirs(args.exhibit)
    if args.exhibit and not exhibit_dirs:
        print(f"unknown exhibit: {args.exhibit}", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    all_exhibit_dirs = list_exhibit_dirs(None)

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
            f"{prefix}: {e}" for e in validate_against_schema(exhibit, "exhibit.schema.json", "exhibit")
        )
        all_errors.extend(
            f"{prefix}: {e}"
            for e in validate_against_schema(manifest, "media-manifest.schema.json", "manifest")
        )
        all_errors.extend(
            f"{prefix}: {e}" for e in validate_slug_match(exhibit_dir, exhibit, manifest)
        )
        all_errors.extend(
            f"{prefix}: {e}" for e in validate_manifest_assets(exhibit_dir, manifest)
        )
        all_errors.extend(
            f"{prefix}: {e}" for e in validate_timeline(exhibit_dir, exhibit, manifest)
        )

    catalog_path = EXHIBITS / "_catalog.yaml"
    if catalog_path.is_file():
        try:
            catalog = load_yaml(catalog_path)
            all_errors.extend(
                validate_against_schema(catalog, "catalog.schema.json", "catalog")
            )
            # Always compare catalog against every exhibit folder.
            all_errors.extend(validate_catalog(catalog, all_exhibit_dirs))
        except (ValueError, OSError) as exc:
            all_errors.append(f"catalog: {exc}")

    all_errors.extend(validate_tree_media_policy())
    if not args.skip_secrets:
        all_errors.extend(validate_secrets())

    if all_errors:
        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique: list[str] = []
        for err in all_errors:
            if err not in seen:
                seen.add(err)
                unique.append(err)
        print("Validation failed:")
        for err in unique:
            print(f"  - {err}")
        return 1

    print(f"OK: {len(exhibit_dirs)} exhibit(s) passed contract validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
