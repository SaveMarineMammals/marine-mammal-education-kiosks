#!/usr/bin/env bash
# Idempotent installer: configure CMS-host content sync (repo, venv, env,
# systemd timer, optional GitHub Actions self-hosted runner).
#
# Run on the CMS mini PC after Xibo is up (see install-cms-host.md).
# Full checklist: ops/runbooks/cms-content-sync.md
set -euo pipefail

MMEK_ROOT="${MMEK_ROOT:-/opt/mmek}"
MMEK_REPO="${MMEK_REPO:-${MMEK_ROOT}/repo}"
MMEK_VENV="${MMEK_VENV:-${MMEK_ROOT}/venv}"
MMEK_RUNNER_DIR="${MMEK_RUNNER_DIR:-${MMEK_ROOT}/actions-runner}"
ENV_FILE="${MMEK_ENV_FILE:-/etc/mmek/cms-sync.env}"
BRANCH="${MMEK_BRANCH:-main}"
RUNNER_LABELS="${MMEK_RUNNER_LABELS:-self-hosted,mmek-cms,Linux,X64}"
REPO_URL=""
RUNNER_TOKEN=""
CMS_URL=""
SKIP_RUNNER=0
SKIP_TIMER=0
RECONFIGURE_RUNNER=0
LIVE_SYNC=0
DRY_RUN_DEPLOY=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage: sudo ./deploy-cms-sync.sh [options]

Options:
  --repo-url URL           Git remote to clone (required on first install)
  --branch NAME            Branch to track (default: main)
  --runner-token TOKEN     GitHub Actions runner registration token
  --cms-url URL            Prefill XIBO_CMS_URL in env file
  --skip-runner            Do not install/configure the self-hosted runner
  --skip-timer             Install units but do not enable the daily timer
  --reconfigure-runner     Force runner config.sh even if already configured
  --live-sync              After smoke dry-run, run a live sync
  --dry-run-deploy         Print actions without changing the system
  -h, --help               Show this help
EOF
}

log() { echo "==> $*"; }
warn() { echo "warning: $*" >&2; }
die() { echo "error: $*" >&2; exit 1; }

run() {
  if [[ "${DRY_RUN_DEPLOY}" -eq 1 ]]; then
    echo "dry-run: $*"
    return 0
  fi
  "$@"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url) REPO_URL="${2:-}"; shift 2 ;;
    --branch) BRANCH="${2:-}"; shift 2 ;;
    --runner-token) RUNNER_TOKEN="${2:-}"; shift 2 ;;
    --cms-url) CMS_URL="${2:-}"; shift 2 ;;
    --skip-runner) SKIP_RUNNER=1; shift ;;
    --skip-timer) SKIP_TIMER=1; shift ;;
    --reconfigure-runner) RECONFIGURE_RUNNER=1; shift ;;
    --live-sync) LIVE_SYNC=1; shift ;;
    --dry-run-deploy) DRY_RUN_DEPLOY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" \
    ${REPO_URL:+--repo-url "$REPO_URL"} \
    --branch "${BRANCH}" \
    ${RUNNER_TOKEN:+--runner-token "$RUNNER_TOKEN"} \
    ${CMS_URL:+--cms-url "$CMS_URL"} \
    $([[ "${SKIP_RUNNER}" -eq 1 ]] && echo --skip-runner) \
    $([[ "${SKIP_TIMER}" -eq 1 ]] && echo --skip-timer) \
    $([[ "${RECONFIGURE_RUNNER}" -eq 1 ]] && echo --reconfigure-runner) \
    $([[ "${LIVE_SYNC}" -eq 1 ]] && echo --live-sync) \
    $([[ "${DRY_RUN_DEPLOY}" -eq 1 ]] && echo --dry-run-deploy)
fi

export DEBIAN_FRONTEND=noninteractive

# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------
log "Installing prerequisites (git, git-lfs, python3, curl, jq)"
run apt-get update -y
run apt-get install -y \
  ca-certificates \
  curl \
  git \
  git-lfs \
  jq \
  python3 \
  python3-venv \
  python3-pip

run git lfs install --system || run git lfs install || true

# ---------------------------------------------------------------------------
# 2. Repo checkout
# ---------------------------------------------------------------------------
run mkdir -p "${MMEK_ROOT}" /etc/mmek /var/lock

if [[ -d "${MMEK_REPO}/.git" ]]; then
  log "Updating existing repo at ${MMEK_REPO}"
  if [[ "${DRY_RUN_DEPLOY}" -eq 0 ]]; then
    git -C "${MMEK_REPO}" fetch --prune origin
    git -C "${MMEK_REPO}" checkout "${BRANCH}"
    git -C "${MMEK_REPO}" reset --hard "origin/${BRANCH}"
    git -C "${MMEK_REPO}" lfs pull || warn "git lfs pull failed"
  else
    echo "dry-run: git fetch/reset in ${MMEK_REPO}"
  fi
else
  [[ -n "${REPO_URL}" ]] || die "--repo-url is required for first clone into ${MMEK_REPO}"
  log "Cloning ${REPO_URL} -> ${MMEK_REPO}"
  run git clone --branch "${BRANCH}" "${REPO_URL}" "${MMEK_REPO}"
  if [[ "${DRY_RUN_DEPLOY}" -eq 0 ]]; then
    git -C "${MMEK_REPO}" lfs pull || warn "git lfs pull failed"
  fi
fi

# Prefer unit files / examples from the checked-out repo.
UNIT_SRC="${MMEK_REPO}/ops/cms/systemd"
ENV_EXAMPLE="${MMEK_REPO}/ops/cms/cms-sync.env.example"
RUN_WRAPPER="${MMEK_REPO}/ops/cms/scripts/run-cms-sync.sh"

# If deploy was launched from a USB/SCP copy before clone, fall back to SCRIPT_DIR.
if [[ ! -f "${ENV_EXAMPLE}" ]]; then
  ENV_EXAMPLE="$(cd "${SCRIPT_DIR}/.." && pwd)/cms-sync.env.example"
fi
if [[ ! -d "${UNIT_SRC}" ]]; then
  UNIT_SRC="$(cd "${SCRIPT_DIR}/../systemd" && pwd)"
fi

[[ -f "${ENV_EXAMPLE}" ]] || die "missing cms-sync.env.example"
[[ -f "${UNIT_SRC}/mmek-cms-sync.service" ]] || die "missing systemd units"
[[ -x "${RUN_WRAPPER}" || -f "${RUN_WRAPPER}" ]] || die "missing run-cms-sync.sh"

run chmod +x "${MMEK_REPO}/ops/cms/scripts/"*.sh

# ---------------------------------------------------------------------------
# 3. Python venv
# ---------------------------------------------------------------------------
log "Creating/updating venv at ${MMEK_VENV}"
if [[ ! -x "${MMEK_VENV}/bin/python" ]]; then
  run python3 -m venv "${MMEK_VENV}"
fi
run "${MMEK_VENV}/bin/python" -m pip install --upgrade pip
run "${MMEK_VENV}/bin/python" -m pip install -r "${MMEK_REPO}/tools/requirements.txt"

# ---------------------------------------------------------------------------
# 4. Secrets / env file
# ---------------------------------------------------------------------------
if [[ ! -f "${ENV_FILE}" ]]; then
  log "Installing ${ENV_FILE} from example (fill OAuth secrets before live sync)"
  run cp "${ENV_EXAMPLE}" "${ENV_FILE}"
  run chmod 600 "${ENV_FILE}"
  if [[ -n "${CMS_URL}" && "${DRY_RUN_DEPLOY}" -eq 0 ]]; then
    if grep -q '^XIBO_CMS_URL=' "${ENV_FILE}"; then
      sed -i "s|^XIBO_CMS_URL=.*|XIBO_CMS_URL=${CMS_URL}|" "${ENV_FILE}"
    else
      printf '\nXIBO_CMS_URL=%s\n' "${CMS_URL}" >> "${ENV_FILE}"
    fi
  fi
else
  log "Keeping existing ${ENV_FILE}"
  run chmod 600 "${ENV_FILE}"
fi

env_ready=0
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  # shellcheck disable=SC1091
  source "${ENV_FILE}" || true
  set +a
  if [[ -n "${XIBO_CMS_URL:-}" && -n "${XIBO_CLIENT_ID:-}" && -n "${XIBO_CLIENT_SECRET:-}" ]]; then
    env_ready=1
  fi
fi

# ---------------------------------------------------------------------------
# 5. systemd units
# ---------------------------------------------------------------------------
log "Installing systemd units"
run cp "${UNIT_SRC}/mmek-cms-sync.service" /etc/systemd/system/mmek-cms-sync.service
run cp "${UNIT_SRC}/mmek-cms-sync.timer" /etc/systemd/system/mmek-cms-sync.timer
run systemctl daemon-reload

if [[ "${SKIP_TIMER}" -eq 0 ]]; then
  if [[ "${env_ready}" -eq 1 ]]; then
    log "Enabling mmek-cms-sync.timer"
    run systemctl enable --now mmek-cms-sync.timer
  else
    warn "OAuth secrets incomplete in ${ENV_FILE}; timer installed but not enabled"
    run systemctl enable mmek-cms-sync.timer || true
    run systemctl stop mmek-cms-sync.timer || true
  fi
else
  log "Skipping timer enable (--skip-timer)"
fi

# ---------------------------------------------------------------------------
# 6. Self-hosted GitHub Actions runner
# ---------------------------------------------------------------------------
if [[ "${SKIP_RUNNER}" -eq 1 ]]; then
  log "Skipping Actions runner (--skip-runner)"
else
  RUNNER_CONFIGURED=0
  if [[ -f "${MMEK_RUNNER_DIR}/.runner" ]]; then
    RUNNER_CONFIGURED=1
  fi

  if [[ "${RUNNER_CONFIGURED}" -eq 1 && "${RECONFIGURE_RUNNER}" -eq 0 ]]; then
    log "Actions runner already configured at ${MMEK_RUNNER_DIR}"
  else
    [[ -n "${RUNNER_TOKEN}" ]] || die \
      "--runner-token is required to configure the self-hosted runner (or pass --skip-runner)"

    # Infer repo slug from remote for runner registration.
    if [[ -z "${REPO_URL}" ]]; then
      REPO_URL="$(git -C "${MMEK_REPO}" remote get-url origin 2>/dev/null || true)"
    fi
    [[ -n "${REPO_URL}" ]] || die "cannot determine --repo-url for runner registration"

    # Normalize to https://github.com/ORG/REPO for config.sh --url
    RUNNER_URL="${REPO_URL}"
    if [[ "${RUNNER_URL}" =~ git@github.com:(.+)\.git$ ]]; then
      RUNNER_URL="https://github.com/${BASH_REMATCH[1]}"
    elif [[ "${RUNNER_URL}" =~ github.com[:/](.+)(\.git)?$ ]]; then
      RUNNER_URL="https://github.com/${BASH_REMATCH[1]%.git}"
    fi

    log "Installing GitHub Actions runner into ${MMEK_RUNNER_DIR}"
    run mkdir -p "${MMEK_RUNNER_DIR}"
    if [[ "${DRY_RUN_DEPLOY}" -eq 0 ]]; then
      if [[ ! -f "${MMEK_RUNNER_DIR}/config.sh" ]]; then
        # Latest linux-x64 runner package via GitHub API.
        RUNNER_VERSION="$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest \
          | jq -r '.tag_name' | sed 's/^v//')"
        [[ -n "${RUNNER_VERSION}" && "${RUNNER_VERSION}" != "null" ]] \
          || die "could not resolve actions/runner version"
        ARCHIVE="actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
        curl -fsSL -o "/tmp/${ARCHIVE}" \
          "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${ARCHIVE}"
        tar -xzf "/tmp/${ARCHIVE}" -C "${MMEK_RUNNER_DIR}"
        rm -f "/tmp/${ARCHIVE}"
      fi
      if [[ "${RECONFIGURE_RUNNER}" -eq 1 && -f "${MMEK_RUNNER_DIR}/.runner" ]]; then
        "${MMEK_RUNNER_DIR}/config.sh" remove --token "${RUNNER_TOKEN}" || true
      fi
      "${MMEK_RUNNER_DIR}/config.sh" \
        --unattended \
        --url "${RUNNER_URL}" \
        --token "${RUNNER_TOKEN}" \
        --name "$(hostname)-mmek-cms" \
        --labels "${RUNNER_LABELS}" \
        --work "_work"
      "${MMEK_RUNNER_DIR}/svc.sh" install
      "${MMEK_RUNNER_DIR}/svc.sh" start
    else
      echo "dry-run: download/configure Actions runner for ${RUNNER_URL}"
    fi
  fi

  if [[ "${DRY_RUN_DEPLOY}" -eq 0 && -f "${MMEK_RUNNER_DIR}/svc.sh" ]]; then
    "${MMEK_RUNNER_DIR}/svc.sh" status || warn "runner service status check failed"
  fi
fi

# ---------------------------------------------------------------------------
# 7. Smoke checks
# ---------------------------------------------------------------------------
log "Smoke checks"

if [[ "${DRY_RUN_DEPLOY}" -eq 0 ]]; then
  if [[ -n "${XIBO_CMS_URL:-}" ]]; then
    if curl -fsS -o /dev/null --max-time 10 "${XIBO_CMS_URL%/}/login"; then
      echo "CMS HTTP OK: ${XIBO_CMS_URL}"
    else
      warn "CMS HTTP probe failed for ${XIBO_CMS_URL}"
    fi
  fi

  if [[ "${env_ready}" -eq 1 ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
    if PYTHONPATH="${MMEK_REPO}/tools" "${MMEK_VENV}/bin/python" -c \
      "from xibo_client import client_from_env; c=client_from_env(); c.ping(); print('OAuth token OK')"; then
      echo "OAuth OK"
    else
      warn "OAuth token probe failed"
      env_ready=0
    fi
  else
    warn "Skipping OAuth probe until ${ENV_FILE} has XIBO_CLIENT_ID/SECRET"
  fi

  log "Dry-run sync"
  MMEK_SKIP_GIT_PULL=1 \
    "${MMEK_VENV}/bin/python" "${MMEK_REPO}/tools/sync_cms.py" \
    --all-published --dry-run --skip-lock || warn "dry-run sync exited non-zero"

  if systemctl is-enabled mmek-cms-sync.timer >/dev/null 2>&1; then
    echo "timer enabled: mmek-cms-sync.timer"
    systemctl list-timers mmek-cms-sync.timer --no-pager || true
  else
    warn "mmek-cms-sync.timer is not enabled"
  fi
fi

# ---------------------------------------------------------------------------
# 8. Optional live sync
# ---------------------------------------------------------------------------
if [[ "${LIVE_SYNC}" -eq 1 ]]; then
  [[ "${env_ready}" -eq 1 ]] || die "--live-sync requires completed OAuth secrets in ${ENV_FILE}"
  log "Running live sync"
  if [[ "${DRY_RUN_DEPLOY}" -eq 0 ]]; then
    MMEK_SKIP_GIT_PULL=1 "${RUN_WRAPPER}" || die "live sync failed"
  else
    echo "dry-run: ${RUN_WRAPPER}"
  fi
fi

echo
echo "Deploy complete."
echo "  Repo:    ${MMEK_REPO}"
echo "  Venv:    ${MMEK_VENV}"
echo "  Env:     ${ENV_FILE}"
echo "  Timer:   mmek-cms-sync.timer"
echo "  Runner:  ${MMEK_RUNNER_DIR} (label mmek-cms)"
echo
if [[ "${env_ready}" -eq 0 ]]; then
  echo "Next:"
  echo "  1. Create a Xibo Applications entry (client_credentials)."
  echo "  2. Edit ${ENV_FILE} with XIBO_CLIENT_ID / XIBO_CLIENT_SECRET."
  echo "  3. Re-run: sudo ${MMEK_REPO}/ops/cms/scripts/deploy-cms-sync.sh --skip-runner"
  echo "  4. Optional first live sync: add --live-sync"
else
  echo "Schedules stay operator-owned: bind campaign mmek-<slug> in the CMS UI."
  echo "See ops/runbooks/cms-content-sync.md"
fi
