#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:?terraform environment directory}"
VAR_FILE="${2:-terraform.tfvars}"

EXTRA=()
if [[ -f "${ROOT_DIR}/${VAR_FILE}" ]]; then
  EXTRA+=("-var-file=${VAR_FILE}")
fi

terraform -chdir="${ROOT_DIR}" apply -input=false -auto-approve "${EXTRA[@]}"
