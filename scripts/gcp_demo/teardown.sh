#!/bin/bash
# Delete the MetricLens real demo fleet (every instance labelled metriclens=true).
set -euo pipefail

PROJECT="${PROJECT_ID:-knudc-yoonwoodev}"

names=$(gcloud compute instances list --project="$PROJECT" \
  --filter="labels.metriclens=true" --format="value(name,zone.basename())")

if [ -z "$names" ]; then
  echo "No metriclens-labelled instances found."
  exit 0
fi

echo "$names" | while read -r name zone; do
  echo "Deleting $name ($zone) ..."
  gcloud compute instances delete "$name" --zone="$zone" --project="$PROJECT" --quiet
done
echo "Teardown complete."
