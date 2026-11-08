#!/usr/bin/env bash
# terraform init with S3 backend config for an environment root.
set -euo pipefail

ROOT_DIR="${1:?terraform environment directory}"
BUCKET="${2:?state bucket}"
KEY="${3:?state key}"
REGION="${4:-us-east-1}"
LOCK_TABLE="${5:?lock table}"

terraform -chdir="${ROOT_DIR}" init -input=false \
  "-backend-config=bucket=${BUCKET}" \
  "-backend-config=key=${KEY}" \
  "-backend-config=region=${REGION}" \
  "-backend-config=dynamodb_table=${LOCK_TABLE}"
