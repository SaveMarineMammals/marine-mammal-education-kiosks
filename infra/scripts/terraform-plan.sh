#!/usr/bin/env bash
# terraform plan without taking the remote lock (safe alongside applies).
set -euo pipefail

ROOT_DIR="${1:?terraform environment directory}"
VAR_FILE="${2:-terraform.tfvars}"

EXTRA=()
if [[ -f "${ROOT_DIR}/${VAR_FILE}" ]]; then
  EXTRA+=("-var-file=${VAR_FILE}")
fi

terraform -chdir="${ROOT_DIR}" plan -input=false -lock=false -out=tfplan "${EXTRA[@]}"

DESTROY="false"
if terraform -chdir="${ROOT_DIR}" show -no-color tfplan | grep -Eiq 'will be destroyed|must be replaced'; then
  DESTROY="true"
  echo "WARNING: plan includes destroys or replacements" >&2
fi
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "destroy_detected=${DESTROY}" >> "${GITHUB_OUTPUT}"
fi
