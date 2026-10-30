#!/bin/bash
# Copy settings whose names start with a prefix from a local env file into the VM's /opt/cbyp/app.env, replacing any
# lines with that prefix there, then re-run the startup script so the app restarts with them (about 10 s of downtime).
# Values are never printed: the file goes over gcloud compute scp and is deleted on both ends.
# Usage: bash deploy/gce/push_env.sh DODO_ [.env.railway]
set -euo pipefail
P=project-b3549f11-8db5-4ca2-9e4
ZONE=us-central1-a
VM=cbyp-web
PREFIX=${1:?usage: push_env.sh PREFIX [env-file]}
FILE=${2:-.env.railway}
[[ $PREFIX =~ ^[A-Z][A-Z0-9_]*$ ]] || { echo "PREFIX must look like DODO_"; exit 1; }

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
grep -E "^${PREFIX}[A-Z0-9_]*=" "$FILE" | tr -d '\r' > "$TMP" || true
[ -s "$TMP" ] || { echo "No ${PREFIX}* settings in $FILE"; exit 1; }
gcloud compute scp "$TMP" "$VM:/tmp/push.env" --zone "$ZONE" --project "$P" --quiet >/dev/null
gcloud compute ssh "$VM" --zone "$ZONE" --project "$P" --quiet --command "
  sudo sh -c 'grep -v ^${PREFIX} /opt/cbyp/app.env > /opt/cbyp/app.env.new; cat /tmp/push.env >> /opt/cbyp/app.env.new;
    chmod 600 /opt/cbyp/app.env.new; mv /opt/cbyp/app.env.new /opt/cbyp/app.env; rm -f /tmp/push.env' &&
  sudo google_metadata_script_runner startup >/dev/null 2>&1 &&
  sudo awk -F= '/^${PREFIX}/{print \"  set on the VM:\", \$1}' /opt/cbyp/app.env"
