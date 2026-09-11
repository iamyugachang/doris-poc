#!/bin/bash
# Build the static demo site with Cloud Build and deploy it to Cloud Run as a public service.
# Usage: deploy/deploy.sh [--dry-run]
#   Needs (one-time, done by this script): run / cloudbuild / artifactregistry APIs enabled on the project.
set -euo pipefail
PROJECT=doris-poc; REGION=asia-east1; SERVICE=doris-ha-demo
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(dirname "$HERE")"
export PATH="$HOME/google-cloud-sdk/bin:$PATH"
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
run(){ if [ $DRY = 1 ]; then echo "[dry-run] $*"; else "$@"; fi; }

# stage only what the image needs: Dockerfile, nginx.conf, the pages, and the per-run logs
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
cp "$HERE/Dockerfile" "$HERE/nginx.conf" "$STAGE/"
mkdir -p "$STAGE/site"; cp "$ROOT/site/index.html" "$ROOT/site/explore.html" "$ROOT/site/specs.html" "$ROOT/site/results.html" "$STAGE/site/"
[ -d "$ROOT/site/results" ] && cp -r "$ROOT/site/results" "$STAGE/site/results"

run gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project="$PROJECT" --quiet
run gcloud run deploy "$SERVICE" --source="$STAGE" --project="$PROJECT" --region="$REGION" \
    --allow-unauthenticated --port=8080 --memory=256Mi --max-instances=2 --quiet
[ $DRY = 1 ] || gcloud run services describe "$SERVICE" --project="$PROJECT" --region="$REGION" --format="value(status.url)"
