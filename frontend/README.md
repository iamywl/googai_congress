# MetricLens AI — Frontend Dashboard

React 19 + Vite SPA visualising server-load metrics, forecasts, and resizing
recommendations from the MetricLens AI backend. Charts use ECharts (Canvas) for
memory-efficient rendering of large time series.

## Live Link

> Updated automatically after deployment. `scripts/deploy.sh deploy` prints the
> Cloud Run URL once the rolling update completes.

- **Live dashboard (Cloud Run)**: https://metriclens-frontend-f2ei3uwvfq-uc.a.run.app

## Local development

```bash
npm install
# Point at a running backend (optional — falls back to deterministic demo data):
VITE_API_BASE_URL=http://localhost:8080 npm run dev
```

Without `VITE_API_BASE_URL`, or if the backend is unreachable, the dashboard
renders deterministic sample data and shows a "demo data" badge.

## Build & quality

```bash
npm run lint      # eslint
npm run build     # production bundle -> dist/ (echarts split into its own chunk)
```

## Screenshots

Automated via Playwright: `node scripts/capture_screenshots.js` (run a
`vite preview` server first). Output: `../docs/screenshots/`.

## Container

Multi-stage `Dockerfile` builds the bundle and serves it from
`nginx-unprivileged` (non-root, port 8080). The backend URL is injected at build
time via the `VITE_API_BASE_URL` build arg.
