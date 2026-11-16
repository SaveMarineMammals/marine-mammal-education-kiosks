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
    payload = {
        "layoutName": PREVIEW_LAYOUT_NAME,
        "layoutId": layout_id,
        "campaignId": full.get("campaignId") or full.get("campaignid"),
        "publishedStatus": full.get("publishedStatus"),
        **summary,
    }
    _agent_debug_log(
        "C",
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
