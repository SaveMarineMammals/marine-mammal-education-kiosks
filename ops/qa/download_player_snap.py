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
    fields = "channel-map,download,revision,confinement,created-at"
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="xibo-player")
    parser.add_argument("--channel", default="stable")
    parser.add_argument("--out", default="xibo-player.snap")
    args = parser.parse_args()

    try:
        data = fetch_snap_info(args.name)
        url, entry = pick_download_url(data, args.channel)
    except urllib.error.HTTPError as exc:
        print(f"Snap Store HTTP {exc.code} for {args.name}: {exc.reason}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1

    ch = entry.get("channel") or {}
    size = (entry.get("download") or {}).get("size")
    print(
        f"Resolved {args.name} "
        f"{ch.get('track')}/{ch.get('risk')} revision={entry.get('revision')} size={size}"
    )
    print(f"Downloading {url} -> {args.out}")
    urllib.request.urlretrieve(url, args.out)
    actual = Path(args.out).stat().st_size
    expected = (entry.get("download") or {}).get("size")
    if expected and actual != int(expected):
        print(
            f"Download size mismatch: got {actual} bytes, expected {expected}",
            file=sys.stderr,
        )
        return 1
    if actual < 1_000_000:
        print(f"Download looks too small ({actual} bytes)", file=sys.stderr)
        return 1
    print(f"Saved {args.out} ({actual} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
