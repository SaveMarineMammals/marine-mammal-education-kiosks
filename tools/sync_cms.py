#!/usr/bin/env python3
"""Reconcile published exhibit media + layouts with Xibo CMS.

Never mutates CMS schedules. Safe for concurrent systemd + Actions via flock.

Usage:
  python tools/sync_cms.py --all-published --dry-run
  python tools/sync_cms.py --exhibit asian-small-clawed-otters
  python tools/sync_cms.py --all-published
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

ROOT = Path(__file__).resolve().parents[1]
EXHIBITS = ROOT / "exhibits"
TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

LOG = logging.getLogger("mmek.sync_cms")

DEFAULT_LOCK = Path(os.environ.get("MMEK_SYNC_LOCK", "/var/lock/mmek-cms-sync.lock"))

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required: pip install pyyaml")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    return data


def discover_published_slugs() -> list[str]:
    slugs: list[str] = []
    if not EXHIBITS.is_dir():
        return slugs
    for path in sorted(EXHIBITS.iterdir()):
        if not path.is_dir() or path.name.startswith("_"):
            continue
        exhibit_path = path / "exhibit.yaml"
        if not exhibit_path.is_file():
            continue
        data = load_yaml(exhibit_path)
        if str(data.get("status") or "").strip() == "published":
            slugs.append(str(data.get("slug") or path.name))
    return slugs


def validate_exhibit(slug: str) -> None:
    cmd = [
        sys.executable,
        str(TOOLS / "validate_exhibits.py"),
        "--exhibit",
        slug,
        "--skip-secrets",
    ]
    LOG.info("Validating %s", slug)
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stdout or "") + (result.stderr or "")
        raise RuntimeError(f"validation failed for {slug}:\n{detail.strip()}")


@contextmanager
def file_lock(lock_path: Path, *, timeout_seconds: int = 3600) -> Iterator[None]:
    """Exclusive flock (POSIX) / msvcrt lock (Windows) around the sync run."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    # /run/lock is wiped on reboot. Whoever creates the file makes it writable
    # by the root systemd unit and the unprivileged Actions runner.
    if os.name != "nt":
        try:
            os.chmod(handle.fileno(), 0o666)
        except OSError:
            pass
    deadline = time.time() + timeout_seconds
    locked = False
    try:
        if os.name == "nt":
            import msvcrt

            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                    break
                except OSError:
                    if time.time() >= deadline:
                        raise RuntimeError(f"timed out waiting for lock {lock_path}")
                    time.sleep(2)
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except BlockingIOError:
                    if time.time() >= deadline:
                        raise RuntimeError(f"timed out waiting for lock {lock_path}")
                    time.sleep(2)
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid={os.getpid()} started={time.time()}\n")
        handle.flush()
        yield
    finally:
        if locked:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def sync_one(
    slug: str,
    *,
    client: Optional[Any],
    dry_run: bool,
) -> dict[str, Any]:
    from sync_media import sync_exhibit_media
    from xibo_layout import upsert_exhibit_layout

    validate_exhibit(slug)
    media_result = sync_exhibit_media(slug, client=client, dry_run=dry_run)
    layout_result = upsert_exhibit_layout(
        client,
        exhibit_slug=slug,
        media_ids=media_result.get("media_ids") or None,
        dry_run=dry_run,
    )
    return {"slug": slug, "media": media_result, "layout": layout_result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--exhibit", help="Sync a single slug (must be published unless --force)")
    group.add_argument(
        "--all-published",
        action="store_true",
        help="Sync every exhibit with status: published",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow syncing a non-published exhibit when --exhibit is set",
    )
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=DEFAULT_LOCK,
        help=f"Exclusive lock path (default {DEFAULT_LOCK})",
    )
    parser.add_argument(
        "--skip-lock",
        action="store_true",
        help="Skip flock (not recommended on the CMS host)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        if args.all_published:
            slugs = discover_published_slugs()
        else:
            slug = args.exhibit
            exhibit = load_yaml(EXHIBITS / slug / "exhibit.yaml")
            status = str(exhibit.get("status") or "").strip()
            if status != "published" and not args.force:
                print(
                    f"error: exhibit {slug!r} status is {status!r}; "
                    "only published exhibits sync (use --force to override)",
                    file=sys.stderr,
                )
                return 1
            slugs = [slug]
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not slugs:
        print("OK: no published exhibits to sync")
        return 0

    print(f"Syncing {len(slugs)} exhibit(s): {', '.join(slugs)}")
    if args.dry_run:
        print("Dry run: no CMS mutations")

    def run() -> int:
        client: Any = None
        if not args.dry_run:
            from xibo_client import XiboError, client_from_env

            try:
                client = client_from_env()
                client.ping()
            except XiboError as exc:
                print(f"error: CMS unavailable: {exc}", file=sys.stderr)
                return 1

        failures = 0
        for slug in slugs:
            try:
                result = sync_one(slug, client=client, dry_run=args.dry_run)
                layout = result["layout"]
                print(
                    f"OK {slug}: layout={layout.get('layout_name')} "
                    f"dry_run={args.dry_run}"
                )
            except Exception as exc:  # noqa: BLE001 — report per-exhibit, fail closed
                failures += 1
                LOG.exception("Sync failed for %s", slug)
                print(f"FAIL {slug}: {exc}", file=sys.stderr)
        if failures:
            print(f"error: {failures}/{len(slugs)} exhibit(s) failed", file=sys.stderr)
            return 1
        print(f"OK: synced {len(slugs)} exhibit(s)")
        return 0

    try:
        if args.skip_lock:
            return run()
        # On developer Windows without /var/lock, fall back beside the repo.
        lock_path = args.lock_file
        if os.name == "nt" and str(lock_path).startswith("/var/"):
            lock_path = ROOT / "dist" / "mmek-cms-sync.lock"
        with file_lock(lock_path):
            return run()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
