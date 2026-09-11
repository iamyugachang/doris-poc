#!/bin/bash
# Terraform wrapper: authenticates the google provider with the current gcloud user (no ADC login needed)
# and fills the operator-specific variables. Usage: infra/tf.sh <terraform args...>
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/google-cloud-sdk/bin:$HOME/.local/bin:$PATH"
export GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)"
export TF_VAR_ssh_user="${TF_VAR_ssh_user:-$USER}"
export TF_VAR_allow_ip="${TF_VAR_allow_ip:-${ALLOW_IP:-$(curl -s -4 ifconfig.me)}}"
cd "$HERE"
[ -d .terraform ] || terraform init -input=false >/dev/null
exec terraform "$@"
