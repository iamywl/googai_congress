#!/usr/bin/env bash
#
# MetricLens AI — GCP Cloud Run deployment driver.
#
# Idempotent: every step is safe to re-run. It bootstraps the project
# (APIs, Artifact Registry), optionally applies the database schema + seed via
# the Cloud SQL Auth Proxy, then triggers the Cloud Build pipeline that builds,
# tests, pushes and deploys both services with a rolling update.
#
# Two ways to deploy:
#   - `deploy`: upload the source from here and build (needs a stable link).
#   - `push`  : git push only; the GitHub trigger builds server-side (robust
#               over an unstable laptop<->GCP link). Set up once with `trigger`.
#
# Usage:
#   PROJECT_ID=knudc-yoonwoodev ./scripts/deploy.sh bootstrap
#   PROJECT_ID=knudc-yoonwoodev CLOUDSQL_INSTANCE=...:...:... \
#     DATABASE_URL=postgresql://... ./scripts/deploy.sh migrate
#   PROJECT_ID=knudc-yoonwoodev ./scripts/deploy.sh deploy   # upload + build here
#   PROJECT_ID=knudc-yoonwoodev ./scripts/deploy.sh trigger  # one-time: create trigger
#   PROJECT_ID=knudc-yoonwoodev ./scripts/deploy.sh push     # deploy via git push
#   PROJECT_ID=knudc-yoonwoodev ./scripts/deploy.sh all
# ------------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID (e.g. knudc-yoonwoodev)}"
REGION="${REGION:-us-central1}"
AR_REPO="${AR_REPO:-metriclens}"
CLOUDSQL_INSTANCE="${CLOUDSQL_INSTANCE:-}"
DB_SECRET="${DB_SECRET:-metriclens-db-url}"

# GitHub-triggered build settings. With a trigger in place the laptop only does
# a small `git push`; Cloud Build then builds and deploys entirely inside
# Google's network, so an unstable laptop<->GCP link no longer blocks deploys.
REPO_OWNER="${REPO_OWNER:-iamywl}"
REPO_NAME="${REPO_NAME:-googai_congress}"
BRANCH="${BRANCH:-main}"
TRIGGER_NAME="${TRIGGER_NAME:-metriclens-main}"

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

# Create (idempotently) a Cloud Build trigger that fires on every push to the
# default branch and runs cloudbuild.yaml server-side. Run this ONCE.
#
# Prerequisite (one-time, console): connect the GitHub repo to Cloud Build by
# installing the "Google Cloud Build" GitHub App on ${REPO_OWNER}/${REPO_NAME}:
#   https://console.cloud.google.com/cloud-build/triggers/connect?project=${PROJECT_ID}
# Without that connection the create call below fails with a repo-not-connected
# error — that is expected; finish the console step and re-run `trigger`.
trigger() {
    log "Ensuring Cloud Build trigger '${TRIGGER_NAME}' exists (idempotent)"
    if gcloud builds triggers describe "${TRIGGER_NAME}" \
            --project "${PROJECT_ID}" >/dev/null 2>&1; then
        echo "    trigger already present — skipping."
        return 0
    fi

    local subs="_REGION=${REGION},_AR_REPO=${AR_REPO}"
    if [[ -n "${CLOUDSQL_INSTANCE}" ]]; then
        subs+=",_CLOUDSQL_INSTANCE=${CLOUDSQL_INSTANCE},_DB_SECRET=${DB_SECRET}"
    fi

    gcloud builds triggers create github \
        --name="${TRIGGER_NAME}" \
        --repo-name="${REPO_NAME}" --repo-owner="${REPO_OWNER}" \
        --branch-pattern="^${BRANCH}\$" \
        --build-config=cloudbuild.yaml \
        --substitutions "${subs}" \
        --project "${PROJECT_ID}"
    log "Trigger created. Future deploys: just run '$0 push'."
}

# Push the branch to GitHub; the trigger then builds & deploys inside Google's
# network. The laptop only does a small, resumable git push — robust over an
# unstable laptop<->GCP link. No source tarball upload (unlike `deploy`).
push() {
    log "Pushing '${BRANCH}' to GitHub — Cloud Build trigger will build & deploy"
    git -C "${ROOT_DIR}" push origin "${BRANCH}"
    log "Build submitted server-side. Watch it (no source upload from here):"
    echo "    gcloud builds list --ongoing --project ${PROJECT_ID}"
    echo "    gcloud builds log --stream <BUILD_ID> --project ${PROJECT_ID}"
    echo "  Or the console:"
    echo "    https://console.cloud.google.com/cloud-build/builds?project=${PROJECT_ID}"
}

case "${1:-all}" in
    bootstrap) bootstrap ;;
    migrate)   migrate ;;
    deploy)    deploy ;;
    trigger)   trigger ;;
    push)      push ;;
    all)       bootstrap; deploy ;;
    *) echo "Usage: $0 {bootstrap|migrate|deploy|trigger|push|all}" >&2; exit 2 ;;
esac
