#!/usr/bin/env bash
#
# MetricLens AI — GCP Cloud Run deployment driver.
#
# Idempotent: every step is safe to re-run. It bootstraps the project
# (APIs, Artifact Registry), optionally applies the database schema + seed via
# the Cloud SQL Auth Proxy, then triggers the Cloud Build pipeline that builds,
# tests, pushes and deploys both services with a rolling update.
#
# Usage:
#   PROJECT_ID=knudc-yoonwoodev ./scripts/deploy.sh bootstrap
#   PROJECT_ID=knudc-yoonwoodev CLOUDSQL_INSTANCE=...:...:... \
#     DATABASE_URL=postgresql://... ./scripts/deploy.sh migrate
#   PROJECT_ID=knudc-yoonwoodev ./scripts/deploy.sh deploy
#   PROJECT_ID=knudc-yoonwoodev ./scripts/deploy.sh all
# ------------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID (e.g. knudc-yoonwoodev)}"
REGION="${REGION:-us-central1}"
AR_REPO="${AR_REPO:-metriclens}"
CLOUDSQL_INSTANCE="${CLOUDSQL_INSTANCE:-}"
DB_SECRET="${DB_SECRET:-metriclens-db-url}"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }

bootstrap() {
    log "Enabling required GCP APIs (idempotent)"
    gcloud services enable \
        run.googleapis.com cloudbuild.googleapis.com \
        artifactregistry.googleapis.com sqladmin.googleapis.com \
        secretmanager.googleapis.com \
        --project "${PROJECT_ID}"

    log "Ensuring Artifact Registry repo '${AR_REPO}' exists"
    if ! gcloud artifacts repositories describe "${AR_REPO}" \
            --location "${REGION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
        gcloud artifacts repositories create "${AR_REPO}" \
            --repository-format=docker --location "${REGION}" \
            --description="MetricLens AI images" --project "${PROJECT_ID}"
    else
        echo "    repo already present — skipping."
    fi
}

migrate() {
    : "${DATABASE_URL:?set DATABASE_URL (a psql/libpq DSN) for migration}"
    log "Applying schema + seed (idempotent) via generate_test_data.sh"
    # schema.sql and the seed both use IF NOT EXISTS / ON CONFLICT, so this is
    # safe to run on every deploy without destroying existing data.
    DATABASE_URL="${DATABASE_URL}" \
        "${ROOT_DIR}/scripts/generate_test_data.sh" --apply --schema
}

deploy() {
    log "Submitting Cloud Build pipeline (build -> test -> deploy)"
    local subs="_REGION=${REGION},_AR_REPO=${AR_REPO}"
    if [[ -n "${CLOUDSQL_INSTANCE}" ]]; then
        subs+=",_CLOUDSQL_INSTANCE=${CLOUDSQL_INSTANCE},_DB_SECRET=${DB_SECRET}"
    fi
    gcloud builds submit "${ROOT_DIR}" \
        --config "${ROOT_DIR}/cloudbuild.yaml" \
        --substitutions "${subs}" \
        --project "${PROJECT_ID}"

    log "Live endpoints:"
    gcloud run services list --region "${REGION}" --project "${PROJECT_ID}" \
        --format='table(metadata.name, status.url)'
}

case "${1:-all}" in
    bootstrap) bootstrap ;;
    migrate)   migrate ;;
    deploy)    deploy ;;
    all)       bootstrap; deploy ;;
    *) echo "Usage: $0 {bootstrap|migrate|deploy|all}" >&2; exit 2 ;;
esac
