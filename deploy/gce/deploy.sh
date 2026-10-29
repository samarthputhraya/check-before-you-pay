#!/bin/bash
# Redeploy the live site: build a git ref (default origin/main) with Cloud Build, then restart the VM's app on it.
# Usage: bash deploy/gce/deploy.sh [git-ref]
set -euo pipefail
P=project-b3549f11-8db5-4ca2-9e4
ZONE=us-central1-a
VM=cbyp-web
REF=${1:-origin/main}

git fetch -q origin
SHA=$(git rev-parse --short "$REF")
IMAGE=us-central1-docker.pkg.dev/$P/cbyp/app:$SHA
SRC=$(mktemp -d)
git archive "$REF" | tar -x -C "$SRC"   # committed files only: never .env, .venv or data
gcloud builds submit "$SRC" --tag "$IMAGE" --project "$P" --quiet
rm -rf "$SRC"
gcloud compute instances add-metadata "$VM" --zone "$ZONE" --project "$P" --metadata image="$IMAGE"
gcloud compute ssh "$VM" --zone "$ZONE" --project "$P" --quiet --command "sudo google_metadata_script_runner startup"
echo "Deployed $SHA"
