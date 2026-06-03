#!/bin/bash
# Provision the MetricLens real demo fleet: small e2 instances that run a diurnal
# CPU load generator, labelled `metriclens=true` so the backend can discover them
# via Cloud Monitoring / the Compute API. Idempotent: skips instances that exist.
#
# Cost (us-central1, on-demand): e2-small ~= $12.2/mo each; 4 instances ~= $49/mo
# (well under the ~$220 / month 300,000 KRW budget). Tear down with teardown.sh.
set -euo pipefail

PROJECT="${PROJECT_ID:-knudc-yoonwoodev}"
ZONE="${ZONE:-us-central1-a}"
MACHINE="${MACHINE:-e2-small}"
DIR="$(cd "$(dirname "$0")" && pwd)"

# name:phase
FLEET=(
  "ml-web-01:web"
  "ml-api-02:api"
  "ml-batch-03:batch"
  "ml-idle-04:idle"
)

echo "Provisioning ${#FLEET[@]} x ${MACHINE} in ${PROJECT}/${ZONE} ..."
for entry in "${FLEET[@]}"; do
  name="${entry%%:*}"
  phase="${entry##*:}"
  if gcloud compute instances describe "$name" --zone="$ZONE" --project="$PROJECT" >/dev/null 2>&1; then
    echo "  = $name already exists, skipping"
    continue
  fi
  echo "  + creating $name (phase=$phase)"
  gcloud compute instances create "$name" \
    --project="$PROJECT" --zone="$ZONE" \
    --machine-type="$MACHINE" \
    --image-family=debian-12 --image-project=debian-cloud \
    --no-address \
    --labels=metriclens=true \
    --metadata=ml-phase="$phase" \
    --metadata-from-file=startup-script="$DIR/startup.sh" \
    --quiet
done

echo
echo "Done. Labelled instances:"
gcloud compute instances list --project="$PROJECT" \
  --filter="labels.metriclens=true" \
  --format="table(name,zone.basename(),machineType.basename(),status)"
echo
echo "Metrics take a few minutes to appear in Cloud Monitoring; a full diurnal"
echo "cycle accrues over ~24h. Tear down anytime with scripts/gcp_demo/teardown.sh."
