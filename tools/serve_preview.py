#!/usr/bin/env python3
"""Serve the repo root so framework/preview can load tokens and exhibit copy.

Usage:
  python tools/serve_preview.py
  python tools/serve_preview.py --port 4173
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    preview_url = f"http://localhost:{args.port}/framework/preview/"

    try:
        with socketserver.TCPServer(("", args.port), handler) as httpd:
            print(f"Serving {ROOT}")
            print(f"Preview: {preview_url}")
            print("Press Ctrl+C to stop.")
            httpd.serve_forever()
    except OSError as exc:
        print(f"Could not bind port {args.port}: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
