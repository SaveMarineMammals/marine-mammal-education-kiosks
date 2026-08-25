#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for the Marine Mammal Education Kiosks repo.
# Installs the durable Python tooling + QA/preview stack after checkout.
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

# Materialize Git LFS media. The environment checks out with GIT_LFS_SKIP_SMUDGE=1,
# so exhibit assets under exhibits/*/media/{assets,previews}/ arrive as pointer
# files; validate_exhibits.py verifies on-disk sha256/bytes and needs real binaries.
# Non-build agents run install on every boot, so this keeps their media fresh; for
# builds-enabled environments (where install runs only at build time) the same pull
# runs per boot from .cursor/start.sh. Idempotent: present objects are a no-op.
git lfs pull

echo "Cloud Agent install complete."
