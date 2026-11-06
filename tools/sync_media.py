#!/usr/bin/env python3
"""Sync exhibit media into Xibo CMS Library.

Resolves repo-relative URIs and optional MEDIA_STORE_URI objects, verifies
sha256, uploads when missing/outdated, places under exhibits/<slug>, and
applies xiboTags plus a CMS-safe sha256 prefix / mmek:managed.

Usage:
  python tools/sync_media.py --exhibit humpback-migration --dry-run
  python tools/sync_media.py --exhibit humpback-migration
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EXHIBITS = ROOT / "exhibits"
TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from pathutil import resolve_manifest_path  # noqa: E402

LOG = logging.getLogger("mmek.sync_media")

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# Xibo CMS rejects a tag outside 1..50 characters (HTTP 422 on library edit).
XIBO_TAG_MAX_LEN = 50
_HASH_TAG_PREFIX = "sha256:"
_HASH_TAG_HEX_LEN = XIBO_TAG_MAX_LEN - len(_HASH_TAG_PREFIX)


def content_hash_tag(digest: str) -> str:
    """CMS tag for a sha256 digest.

    The manifest keeps the full 64-hex digest. Xibo tags cannot hold
    ``sha256:`` plus that digest (71 characters), so the library tag stores
    the first 43 hex digits. Sync still verifies file bytes against the full
    digest before upload.
    """
    hex_digest = digest.strip().lower()
    if not hex_digest:
        raise ValueError("sha256 digest is empty")
    return f"{_HASH_TAG_PREFIX}{hex_digest[:_HASH_TAG_HEX_LEN]}"


def library_tags(slug: str, asset_tags: list[Any], digest: str) -> list[str]:
    """Tags applied to one Library item, all within Xibo's length limit."""
    tags = [str(t).strip() for t in asset_tags if str(t).strip()]
    tags = [t for t in tags if not t.lower().startswith(_HASH_TAG_PREFIX)]
    exhibit_tag = f"exhibit:{slug}"
    if exhibit_tag not in tags:
        tags.insert(0, exhibit_tag)
    if "mmek:managed" not in tags:
        tags.append("mmek:managed")
    if digest.strip():
        tags.append(content_hash_tag(digest))
    for tag in tags:
        if not 1 <= len(tag) <= XIBO_TAG_MAX_LEN:
            raise ValueError(
                f"Xibo tag must be 1-{XIBO_TAG_MAX_LEN} characters "
                f"(got {len(tag)}): {tag}"
            )
    return tags


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _media_store_root() -> Optional[Path]:
    raw = (os.environ.get("MEDIA_STORE_URI") or "").strip()
    if not raw:
        return None
    if raw.startswith("file://"):
        parsed = urlparse(raw)
        # file:///path or file://localhost/path
        path = parsed.path
        if parsed.netloc and parsed.netloc not in {"", "localhost"}:
            path = f"/{parsed.netloc}{path}"
        return Path(path)
    if "://" not in raw:
        return Path(raw)
    return None


def _is_store_key(uri: str) -> bool:
    text = (uri or "").strip()
    if not text:
        return False
    if text.startswith("sha256/"):
        return True
    if text.startswith("s3://"):
        return True
    # Repo-relative paths typically start with exhibits/ or framework/
    if text.startswith("exhibits/") or text.startswith("framework/"):
        return False
    if "://" in text:
        return True
    return False


def resolve_asset_bytes(asset: dict[str, Any], *, slug: str) -> Path:
    """Return a local file path for the asset (may be a temp download)."""
    uri = str(asset.get("uri") or "").strip()
    filename = str(asset.get("filename") or "").strip()
    exhibit_dir = EXHIBITS / slug

    if uri and not _is_store_key(uri):
        path = resolve_manifest_path(uri, root=ROOT)
        if path.is_file():
            return path
        if filename:
            fallback = exhibit_dir / "media" / "assets" / filename
            if fallback.is_file():
                return fallback
        raise FileNotFoundError(f"repo asset not found: {uri}")

    if filename:
        local = exhibit_dir / "media" / "assets" / filename
        if local.is_file():
            return local

    store_root = _media_store_root()
    if uri.startswith("s3://"):
        return _fetch_s3_uri(uri)
    if store_root is None:
        raise FileNotFoundError(
            f"asset {asset.get('id')!r} needs MEDIA_STORE_URI or a local file "
            f"(uri={uri!r})"
        )
    # Prefer content-addressed key under the store root.
    key = uri
    if key.startswith("sha256/"):
        candidate = store_root / key
    else:
        candidate = store_root / key
    if candidate.is_file():
        return candidate
    if filename:
        by_name = store_root / slug / filename
        if by_name.is_file():
            return by_name
    raise FileNotFoundError(f"store object not found: {candidate}")


def _fetch_s3_uri(uri: str) -> Path:
    try:
        import boto3  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "s3:// media requires boto3: pip install boto3 "
            "(or mount the store and set MEDIA_STORE_URI=file://...)"
        ) from exc
    parsed = urlparse(uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    suffix = Path(key).suffix or ".bin"
    tmp = tempfile.NamedTemporaryFile(prefix="mmek-media-", suffix=suffix, delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    LOG.info("Downloading s3://%s/%s -> %s", bucket, key, tmp_path)
    boto3.client("s3").download_file(bucket, key, str(tmp_path))
    return tmp_path


def plan_uploads(manifest: dict) -> list[dict]:
    assets = manifest.get("assets") or []
    return [a for a in assets if isinstance(a, dict)]


def library_name_for(slug: str, asset: dict[str, Any]) -> str:
    asset_id = str(asset.get("id") or "asset").strip()
    return f"{slug}-{asset_id}"


def sync_exhibit_media(
    slug: str,
    *,
    client: Any = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Sync one exhibit's manifest assets. Returns media_ids map and stats."""
    manifest = load_manifest(slug)
    planned = plan_uploads(manifest)
    folder_id = None
    if client is not None and not dry_run:
        folder_id = client.ensure_folder_path(["exhibits", slug])

    media_ids: dict[str, int] = {}
    uploaded = 0
    reused = 0
    temp_paths: list[Path] = []

    try:
        for asset in planned:
            asset_id = str(asset.get("id") or "").strip()
            if not asset_id:
                continue
            expected = str(asset.get("sha256") or "").strip().lower()
            name = library_name_for(slug, asset)
            tags = library_tags(slug, asset.get("xiboTags") or [], expected)
            hash_tag = content_hash_tag(expected) if expected else ""

            if dry_run or client is None:
                print(
                    f"  - {asset_id}: {asset.get('uri')} "
                    f"-> Library exhibits/{slug}/ ({asset.get('filename')}) as {name}"
                )
                continue

            existing = client.find_media_by_name(name)
            if existing is not None and hash_tag and client.media_has_tag(
                existing, hash_tag
            ):
                mid = int(existing.get("mediaId") or existing.get("id"))
                media_ids[asset_id] = mid
                reused += 1
                LOG.info("Reuse mediaId=%s name=%s (sha256 match)", mid, name)
                continue

            path = resolve_asset_bytes(asset, slug=slug)
            if path.name.startswith("mmek-media-"):
                temp_paths.append(path)
            actual = sha256_file(path)
            if expected and actual.lower() != expected:
                raise ValueError(
                    f"sha256 mismatch for {asset_id}: expected {expected}, got {actual}"
                )

            mid = client.upload_media(path, name=name)
            client.edit_media(mid, name=name, tags=tags, folder_id=folder_id)
            media_ids[asset_id] = mid
            uploaded += 1
            LOG.info("Synced mediaId=%s name=%s", mid, name)
    finally:
        for path in temp_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    return {
        "slug": slug,
        "planned": len(planned),
        "uploaded": uploaded,
        "reused": reused,
        "media_ids": media_ids,
        "dry_run": dry_run or client is None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exhibit", required=True, help="Exhibit slug")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned uploads without contacting store or CMS",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        manifest = load_manifest(args.exhibit)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    planned = plan_uploads(manifest)
    print(f"Exhibit: {args.exhibit}")
    print(f"Store: {manifest.get('store', '(unset)')}")
    print(f"Assets to sync: {len(planned)}")

    if args.dry_run:
        for asset in planned:
            print(
                f"  - {asset.get('id')}: {asset.get('uri')} "
                f"-> Library exhibits/{args.exhibit}/ ({asset.get('filename')})"
            )
        print("Dry run only; no uploads performed.")
        return 0

    try:
        from xibo_client import XiboError, client_from_env
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        client = client_from_env()
        result = sync_exhibit_media(args.exhibit, client=client, dry_run=False)
    except (OSError, RuntimeError, ValueError, XiboError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"OK: uploaded={result['uploaded']} reused={result['reused']} "
        f"total={result['planned']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
