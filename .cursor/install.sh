#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for the Marine Mammal Education Kiosks repo.
# Prepares the Python tooling and QA/preview stack after the repo is checked out.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# 1. Real LFS binaries. validate_exhibits.py verifies sha256/bytes for repo-relative
#    assets, so CI-equivalent runs need the actual files, not pointers.
#    --skip-repo configures LFS filters globally without clobbering managed git hooks.
git lfs install --skip-repo >/dev/null 2>&1 || true
git lfs pull

# 2. Python dependencies. Debian's Python is PEP 668 "externally managed", so
#    --break-system-packages installs into the environment's site-packages.
PIP_INSTALL=(python3 -m pip install --break-system-packages)
"${PIP_INSTALL[@]}" -r tools/requirements.txt
"${PIP_INSTALL[@]}" -r ops/qa/requirements.txt

# 3. Chromium + OS libraries for the Tier 2 timeline preview (ci_timeline_preview.py).
#    --with-deps invokes sudo apt-get internally; both are idempotent.
python3 -m playwright install --with-deps chromium

echo "Cloud Agent environment ready."
