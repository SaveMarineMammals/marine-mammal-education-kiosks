#!/usr/bin/env bash
# Pull main (when configured) and reconcile published exhibits with Xibo CMS.
# Invoked by systemd timer and usable manually on the CMS host.
set -euo pipefail

MMEK_REPO="${MMEK_REPO:-/opt/mmek/repo}"
MMEK_VENV="${MMEK_VENV:-/opt/mmek/venv}"
MMEK_BRANCH="${MMEK_BRANCH:-main}"
ENV_FILE="${MMEK_ENV_FILE:-/etc/mmek/cms-sync.env}"
LOCK_FILE="${MMEK_SYNC_LOCK:-/var/lock/mmek-cms-sync.lock}"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a
fi

if [[ ! -d "${MMEK_REPO}/.git" ]]; then
  echo "error: repo missing at ${MMEK_REPO}" >&2
  exit 1
fi

if [[ ! -x "${MMEK_VENV}/bin/python" ]]; then
  echo "error: venv missing at ${MMEK_VENV}" >&2
  exit 1
fi

cd "${MMEK_REPO}"

if [[ "${MMEK_SKIP_GIT_PULL:-0}" != "1" ]]; then
  echo "==> Updating ${MMEK_REPO} (${MMEK_BRANCH})"
  git fetch --prune origin
  git checkout "${MMEK_BRANCH}"
  git reset --hard "origin/${MMEK_BRANCH}"
  if command -v git-lfs >/dev/null 2>&1; then
    git lfs pull
  else
    echo "warning: git-lfs not found; media binaries may be missing" >&2
  fi
fi

echo "==> Running tools/sync_cms.py --all-published"
exec "${MMEK_VENV}/bin/python" tools/sync_cms.py \
  --all-published \
  --lock-file "${LOCK_FILE}" \
  "$@"
