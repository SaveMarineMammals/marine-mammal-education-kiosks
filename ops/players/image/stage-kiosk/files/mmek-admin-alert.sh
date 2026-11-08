#!/usr/bin/env bash
# POST a permanent-failure alert to the MMEK admin-alert Lambda.
# Usage: mmek-admin-alert.sh <code> [detail...]
# Env: /etc/mmek/alert.env (ALERT_LAMBDA_URL, ALERT_INGEST_TOKEN) and optional
#      ALERT_ROLE (cms|player), ALERT_HOSTNAME.
set -euo pipefail

ENV_FILE="${MMEK_ALERT_ENV:-/etc/mmek/alert.env}"
DEDUP_DIR="${MMEK_ALERT_DEDUP_DIR:-/var/lib/mmek/alert-sent}"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <code> [detail...]" >&2
  exit 2
fi

CODE="$1"
shift
DETAIL="${*:-"(no detail)"}"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  # shellcheck disable=SC1091
  source "${ENV_FILE}"
  set +a
fi

: "${ALERT_LAMBDA_URL:?ALERT_LAMBDA_URL required in ${ENV_FILE}}"
: "${ALERT_INGEST_TOKEN:?ALERT_INGEST_TOKEN required in ${ENV_FILE}}"

ROLE="${ALERT_ROLE:-cms}"
HOST="${ALERT_HOSTNAME:-$(hostname -f 2>/dev/null || hostname)}"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

install -d -m 0755 "${DEDUP_DIR}"
SAFE_CODE="$(printf '%s' "${CODE}" | tr -c 'A-Za-z0-9._-' '_')"
DEDUP_FILE="${DEDUP_DIR}/${SAFE_CODE}"
if [[ -f "${DEDUP_FILE}" ]]; then
  echo "mmek-admin-alert: dedup skip code=${CODE}" >&2
  exit 0
fi

PAYLOAD="$(
  HOST="${HOST}" ROLE="${ROLE}" CODE="${CODE}" DETAIL="${DETAIL}" TS="${TS}" python3 - <<'PY'
import json, os
print(json.dumps({
    "host": os.environ["HOST"],
    "role": os.environ["ROLE"],
    "code": os.environ["CODE"],
    "detail": os.environ["DETAIL"],
    "ts": os.environ["TS"],
}))
PY
)"

TMP_BODY="$(mktemp)"
trap 'rm -f "${TMP_BODY}"' EXIT

HTTP_CODE="$(curl -sS -o "${TMP_BODY}" -w '%{http_code}' \
  -X POST "${ALERT_LAMBDA_URL}" \
  -H "Authorization: Bearer ${ALERT_INGEST_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "${PAYLOAD}" || true)"

BODY="$(cat "${TMP_BODY}" 2>/dev/null || true)"

if [[ "${HTTP_CODE}" != "200" && "${HTTP_CODE}" != "207" ]]; then
  echo "mmek-admin-alert: lambda HTTP ${HTTP_CODE}: ${BODY}" >&2
  exit 1
fi

printf '%s\n' "sent_at=${TS}" "http=${HTTP_CODE}" > "${DEDUP_FILE}"
chmod 0644 "${DEDUP_FILE}"
echo "mmek-admin-alert: sent code=${CODE} http=${HTTP_CODE}"
