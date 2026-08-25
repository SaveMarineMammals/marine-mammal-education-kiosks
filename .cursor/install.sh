#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for the Marine Mammal Education Kiosks repo.
# Installs the durable Python tooling + QA/preview stack after checkout. This runs
# at build time (captured in the environment snapshot) and on just-in-time boots;
# per-boot Git LFS materialization lives in .cursor/start.sh instead.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Python dependencies. Debian's Python is PEP 668 "externally managed", so
# --break-system-packages installs into the environment's site-packages.
PIP_INSTALL=(python3 -m pip install --break-system-packages)
"${PIP_INSTALL[@]}" -r tools/requirements.txt
"${PIP_INSTALL[@]}" -r ops/qa/requirements.txt

# Chromium + OS libraries for the Tier 2 timeline preview (ci_timeline_preview.py).
# --with-deps invokes sudo apt-get internally; both are idempotent.
python3 -m playwright install --with-deps chromium

echo "Cloud Agent install complete."
