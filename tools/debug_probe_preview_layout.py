#!/usr/bin/env python3
"""Probe published mmek-preview layout for widget/media wiring (debug session).

Usage on CMS host (same env as sync):
  sudo -E bash -c 'set -a; source /etc/mmek/cms-sync.env; set +a; \
    /opt/mmek/venv/bin/python tools/debug_probe_preview_layout.py'
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from xibo_client import XiboClient, XiboError  # noqa: E402
from xibo_layout import (  # noqa: E402
    PREVIEW_LAYOUT_NAME,
    _agent_debug_log,
    _widgets_media_summary,
)


def main() -> int:
    base = (os.environ.get("XIBO_CMS_URL") or "").strip()
    client_id = (os.environ.get("XIBO_CLIENT_ID") or "").strip()
    secret = (os.environ.get("XIBO_CLIENT_SECRET") or "").strip()
    if not base or not client_id or not secret:
        print("error: need XIBO_CMS_URL, XIBO_CLIENT_ID, XIBO_CLIENT_SECRET", file=sys.stderr)
        return 2
    client = XiboClient(base_url=base)
    client.obtain_token(client_id, secret)
    layout = client.find_layout_by_name(PREVIEW_LAYOUT_NAME)
    if not layout:
        _agent_debug_log(
            "D",
            "debug_probe_preview_layout.py:main",
            "layout_missing",
            {"layoutName": PREVIEW_LAYOUT_NAME},
            run_id="probe",
        )
        print(f"error: layout {PREVIEW_LAYOUT_NAME!r} not found", file=sys.stderr)
        return 1
    layout_id = int(layout.get("layoutId") or layout.get("layoutid") or 0)
    full = client.get_layout(layout_id=layout_id) or layout
    summary = _widgets_media_summary(full if isinstance(full, dict) else {})

    # Hypothesis F/G: image widgets present but duration/useDuration or library bytes bad.
    widget_details: list[dict] = []
    media_details: list[dict] = []
    seen_media: set[int] = set()
    for region in full.get("regions") or []:
        if not isinstance(region, dict):
            continue
        playlists = region.get("regionPlaylist") or region.get("playlists") or []
        if isinstance(playlists, dict):
            playlists = [playlists]
        widgets = []
        for pl in playlists if isinstance(playlists, list) else []:
            if isinstance(pl, dict):
                for w in pl.get("widgets") or []:
                    if isinstance(w, dict):
                        widgets.append(w)
        for w in region.get("widgets") or []:
            if isinstance(w, dict):
                widgets.append(w)
        for w in widgets:
            wtype = str(w.get("type") or "")
            mids = w.get("mediaIds") or w.get("mediaids") or []
            if not isinstance(mids, list):
                mids = [mids] if mids else []
            widget_details.append(
                {
                    "regionId": region.get("regionId") or region.get("regionid"),
                    "widgetId": w.get("widgetId") or w.get("widgetid"),
                    "type": wtype,
                    "duration": w.get("duration"),
                    "useDuration": w.get("useDuration"),
                    "mediaIds": mids,
                }
            )
            for mid in mids:
                try:
                    mid_i = int(mid)
                except (TypeError, ValueError):
                    continue
                if mid_i in seen_media:
                    continue
                seen_media.add(mid_i)
                try:
                    item = client.get_media(mid_i)
                except XiboError as exc:
                    media_details.append({"mediaId": mid_i, "error": str(exc)})
                    continue
                media_details.append(
                    {
                        "mediaId": mid_i,
                        "name": item.get("name"),
                        "mediaType": item.get("mediaType") or item.get("type"),
                        "duration": item.get("duration"),
                        "fileSize": item.get("fileSize") or item.get("size"),
                        "storedAs": item.get("storedAs") or item.get("filename"),
                        "md5": item.get("md5"),
                        "retired": item.get("retired"),
                        "width": item.get("width"),
                        "height": item.get("height"),
                    }
                )

    payload = {
        "layoutName": PREVIEW_LAYOUT_NAME,
        "layoutId": layout_id,
        "campaignId": full.get("campaignId") or full.get("campaignid"),
        "publishedStatus": full.get("publishedStatus"),
        "status": full.get("status"),
        **summary,
        "widgetDetails": widget_details,
        "mediaDetails": media_details,
    }
    _agent_debug_log(
        "F",
        "debug_probe_preview_layout.py:main",
        "existing_preview_layout_probe",
        payload,
        run_id="probe",
    )
    print(json.dumps(payload, indent=2, default=str))
    print(f"\nWrote NDJSON to {ROOT / 'debug-b04d48.log'}", flush=True)
    print(f"probe_ts={int(time.time() * 1000)}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except XiboError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
