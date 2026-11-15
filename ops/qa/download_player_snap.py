#!/usr/bin/env python3
"""Download a Snap Store package for extraction inside Dockerfile.player."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def fetch_snap_info(name: str) -> dict:
    # `download` must be requested explicitly or channel-map entries omit URLs.
    fields = "channel-map,download,revision,confinement,created-at,version"
    req = urllib.request.Request(
        f"https://api.snapcraft.io/v2/snaps/info/{name}?fields={fields}",
        headers={
            "Snap-Device-Series": "16",
            "Snap-Device-Architecture": "amd64",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def pick_download_url(data: dict, channel: str) -> tuple[str, dict]:
    entries = data.get("channel-map") or []
    wanted = channel.lower()

    def matches(entry: dict) -> bool:
        ch = entry.get("channel") or {}
        return wanted in {
            str(ch.get("name") or "").lower(),
            str(ch.get("risk") or "").lower(),
            str(ch.get("track") or "").lower(),
            f"{ch.get('track')}/{ch.get('risk')}".lower(),
        }

    ordered = [e for e in entries if matches(e)] + [e for e in entries if not matches(e)]
    for entry in ordered:
        url = ((entry.get("download") or {}).get("url") or "").strip()
        if url:
            return url, entry

    available = []
    for entry in entries:
        ch = entry.get("channel") or {}
        available.append(
            f"{ch.get('track')}/{ch.get('risk')} arch={ch.get('architecture')} "
            f"rev={entry.get('revision')}"
        )
    raise RuntimeError(
        f"No download URL for snap channel={channel!r}. Available: {available or ['<none>']}"
    )


def revision_download_url(data: dict, revision: int) -> tuple[str, dict]:
    """Build a direct snap download URL for a pinned revision.

    Channel tips only expose the current revision; older revisions remain
    downloadable via snap-id + revision when the Store still hosts them.
    """
    snap_id = (data.get("snap-id") or "").strip()
    if not snap_id:
        raise RuntimeError(f"Snap info missing snap-id for {data.get('name')!r}")

    url = f"https://api.snapcraft.io/api/v1/snaps/download/{snap_id}_{revision}.snap"
    # Prefer metadata from channel-map when this revision is still a tip.
    for entry in data.get("channel-map") or []:
        if int(entry.get("revision") or -1) == revision:
            tip_url = ((entry.get("download") or {}).get("url") or "").strip()
            return tip_url or url, entry

    return url, {
        "revision": revision,
        "version": None,
        "channel": {"track": "latest", "risk": "pinned"},
        "download": {"url": url},
    }


def save_download(url: str, out: Path, expected_size: int | None) -> None:
    print(f"Downloading {url} -> {out}")
    urllib.request.urlretrieve(url, out)
    actual = out.stat().st_size
    if expected_size and actual != int(expected_size):
        raise RuntimeError(
            f"Download size mismatch: got {actual} bytes, expected {expected_size}"
        )
    if actual < 1_000_000:
        raise RuntimeError(f"Download looks too small ({actual} bytes)")
    print(f"Saved {out} ({actual} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="xibo-player")
    parser.add_argument("--channel", default="stable")
    parser.add_argument(
        "--revision",
        type=int,
        default=None,
        help="Pin a Snap Store revision (preferred for QA reproducibility).",
    )
    parser.add_argument("--out", default="xibo-player.snap")
    args = parser.parse_args()

    try:
        data = fetch_snap_info(args.name)
        if args.revision is not None:
            url, entry = revision_download_url(data, args.revision)
        else:
            url, entry = pick_download_url(data, args.channel)
    except urllib.error.HTTPError as exc:
        print(f"Snap Store HTTP {exc.code} for {args.name}: {exc.reason}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    ch = entry.get("channel") or {}
    size = (entry.get("download") or {}).get("size")
    version = entry.get("version") or ("1.8-R6" if entry.get("revision") == 108 else "unknown")
    print(
        f"Resolved {args.name} "
        f"{ch.get('track')}/{ch.get('risk')} revision={entry.get('revision')} "
        f"version={version} size={size}"
    )
    try:
        save_download(url, Path(args.out), int(size) if size else None)
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
