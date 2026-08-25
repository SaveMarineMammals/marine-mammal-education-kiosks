#!/usr/bin/env bash
# Per-boot startup for the Marine Mammal Education Kiosks repo.
#
# Cursor re-checks out the repository on every boot, but with environment builds
# the install phase only runs once (at build time). Git LFS media therefore has
# to be re-materialized on each boot, otherwise exhibit assets under
# exhibits/*/media/{assets,previews}/ arrive as pointer files and
# validate_exhibits.py (which verifies on-disk sha256/bytes) and the timeline
# preview both fail. This is idempotent: already-present objects are a no-op.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

git lfs pull

echo "Git LFS media ready."
