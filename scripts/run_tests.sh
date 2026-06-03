#!/usr/bin/env bash
#
# MetricLens AI — local quality gate (lint -> static analysis -> tests).
# Fail-fast: any stage that fails aborts the run with a non-zero exit code,
# mirroring the Cloud Build pipeline so failures surface before a push.
#
# Usage:
#   ./scripts/run_tests.sh              # backend gate (+ frontend if present)
#   SKIP_FRONTEND=1 ./scripts/run_tests.sh
# ------------------------------------------------------------------------------

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

echo "==> [1/3] Backend lint & static analysis (ruff)"
cd "${BACKEND_DIR}"
if [[ -d .venv ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi
ruff check .

echo "==> [2/3] Backend unit & integration tests (pytest)"
python -m pytest -q

if [[ "${SKIP_FRONTEND:-0}" != "1" && -f "${FRONTEND_DIR}/package.json" ]]; then
    echo "==> [3/3] Frontend lint & build"
    cd "${FRONTEND_DIR}"
    if [[ -d node_modules ]]; then
        npm run lint --if-present
        npm run build --if-present
    else
        echo "    node_modules absent — run 'npm install' first; skipping."
    fi
else
    echo "==> [3/3] Frontend stage skipped"
fi

echo "==> All quality gates passed."
