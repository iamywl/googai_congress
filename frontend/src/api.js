// API client for the MetricLens AI backend.
//
// The base URL is injected at build time via VITE_API_BASE_URL (Cloud Run URL
// in production). When the backend is unreachable -- e.g. local preview or the
// automated screenshot run -- every call transparently falls back to a
// deterministic in-memory sample so the dashboard always renders.

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Deterministic diurnal CPU profile (matches the backend demo seed).
const DAILY_CPU = [
  34, 32, 30, 30, 31, 33, 40, 50, 62, 70, 76, 80,
  83, 85, 84, 80, 74, 66, 58, 50, 44, 40, 37, 35,
];

function sampleSeries(hostOffset = 0) {
  const start = Date.UTC(2024, 0, 1, 0, 0, 0);
  return Array.from({ length: 48 }, (_, i) => {
    const cpu = Math.min(100, DAILY_CPU[i % 24] + hostOffset + Math.floor(i / 12));
    return {
      ts: new Date(start + i * 3600_000).toISOString(),
      cpu_pct: cpu,
      mem_pct: Math.min(100, Math.round(cpu * 0.7 + 20)),
      net_in_kbps: cpu * 120 + 50,
      net_out_kbps: cpu * 80 + 30,
    };
  });
}

// Compact mirror of the backend GCP machine-type catalogue, used as the demo
// fallback (and for client-side "nearest instance" labelling when the backend
// recommendation omits it). Memory is in MB.
const GB = 1024;
export const SAMPLE_MACHINE_TYPES = [
  { name: 'e2-small', series: 'E2', category: 'General purpose (cost-optimised)', vcpu: 2, memory_mb: 2 * GB },
  { name: 'e2-medium', series: 'E2', category: 'General purpose (cost-optimised)', vcpu: 2, memory_mb: 4 * GB },
  { name: 'e2-standard-2', series: 'E2', category: 'General purpose (cost-optimised)', vcpu: 2, memory_mb: 8 * GB },
  { name: 'e2-standard-4', series: 'E2', category: 'General purpose (cost-optimised)', vcpu: 4, memory_mb: 16 * GB },
  { name: 'e2-standard-8', series: 'E2', category: 'General purpose (cost-optimised)', vcpu: 8, memory_mb: 32 * GB },
  { name: 'e2-standard-16', series: 'E2', category: 'General purpose (cost-optimised)', vcpu: 16, memory_mb: 64 * GB },
  { name: 'e2-standard-32', series: 'E2', category: 'General purpose (cost-optimised)', vcpu: 32, memory_mb: 128 * GB },
  { name: 'n2-highcpu-8', series: 'N2', category: 'General purpose (high-CPU)', vcpu: 8, memory_mb: 8 * GB },
  { name: 'n2-highcpu-16', series: 'N2', category: 'General purpose (high-CPU)', vcpu: 16, memory_mb: 16 * GB },
  { name: 'n2-highcpu-32', series: 'N2', category: 'General purpose (high-CPU)', vcpu: 32, memory_mb: 32 * GB },
  { name: 'n2-standard-2', series: 'N2', category: 'General purpose (balanced)', vcpu: 2, memory_mb: 8 * GB },
  { name: 'n2-standard-4', series: 'N2', category: 'General purpose (balanced)', vcpu: 4, memory_mb: 16 * GB },
  { name: 'n2-standard-8', series: 'N2', category: 'General purpose (balanced)', vcpu: 8, memory_mb: 32 * GB },
  { name: 'n2-standard-16', series: 'N2', category: 'General purpose (balanced)', vcpu: 16, memory_mb: 64 * GB },
  { name: 'n2-standard-32', series: 'N2', category: 'General purpose (balanced)', vcpu: 32, memory_mb: 128 * GB },
  { name: 'n2-standard-48', series: 'N2', category: 'General purpose (balanced)', vcpu: 48, memory_mb: 192 * GB },
  { name: 'n2-standard-64', series: 'N2', category: 'General purpose (balanced)', vcpu: 64, memory_mb: 256 * GB },
  { name: 'n2-standard-80', series: 'N2', category: 'General purpose (balanced)', vcpu: 80, memory_mb: 320 * GB },
  { name: 'n2-highmem-8', series: 'N2', category: 'General purpose (high-memory)', vcpu: 8, memory_mb: 64 * GB },
  { name: 'n2-highmem-16', series: 'N2', category: 'General purpose (high-memory)', vcpu: 16, memory_mb: 128 * GB },
  { name: 'n2-highmem-32', series: 'N2', category: 'General purpose (high-memory)', vcpu: 32, memory_mb: 256 * GB },
  { name: 'c2-standard-4', series: 'C2', category: 'Compute-optimised', vcpu: 4, memory_mb: 16 * GB },
  { name: 'c2-standard-8', series: 'C2', category: 'Compute-optimised', vcpu: 8, memory_mb: 32 * GB },
  { name: 'c2-standard-16', series: 'C2', category: 'Compute-optimised', vcpu: 16, memory_mb: 64 * GB },
  { name: 'c2-standard-30', series: 'C2', category: 'Compute-optimised', vcpu: 30, memory_mb: 120 * GB },
  { name: 'c2-standard-60', series: 'C2', category: 'Compute-optimised', vcpu: 60, memory_mb: 240 * GB },
  { name: 'c3-standard-4', series: 'C3', category: 'Compute-optimised (latest gen)', vcpu: 4, memory_mb: 16 * GB },
  { name: 'c3-standard-8', series: 'C3', category: 'Compute-optimised (latest gen)', vcpu: 8, memory_mb: 32 * GB },
  { name: 'c3-standard-22', series: 'C3', category: 'Compute-optimised (latest gen)', vcpu: 22, memory_mb: 88 * GB },
  { name: 'c3-standard-44', series: 'C3', category: 'Compute-optimised (latest gen)', vcpu: 44, memory_mb: 176 * GB },
  { name: 'c3-standard-88', series: 'C3', category: 'Compute-optimised (latest gen)', vcpu: 88, memory_mb: 352 * GB },
];

// Smallest catalogue entry that covers a (vcpu, memory) demand — the client-side
// twin of the backend nearest_fit, used to label hosts/recommendations.
export function nearestMachineType(vcpu, memoryMb, catalog = SAMPLE_MACHINE_TYPES) {
  const exact = catalog.find((m) => m.vcpu === vcpu && m.memory_mb === memoryMb);
  if (exact) return exact;
  const fits = catalog
    .filter((m) => m.vcpu >= vcpu && m.memory_mb >= memoryMb)
    .sort((a, b) => a.vcpu - b.vcpu || a.memory_mb - b.memory_mb);
  if (fits.length) return fits[0];
  return [...catalog].sort((a, b) => b.vcpu - a.vcpu || b.memory_mb - a.memory_mb)[0];
}

// Mirrors the backend demo fleet (app/seed.py) so the offline fallback shows the
// same six research-grounded archetypes.
export const SAMPLE_HOSTS = [
  { id: 'sample-host-1', hostname: 'web-prod-01', environment: 'PROD', vcpu_count: 16, memory_mb: 32768 },
  { id: 'sample-host-2', hostname: 'api-prod-04', environment: 'PROD', vcpu_count: 8, memory_mb: 16384 },
  { id: 'sample-host-3', hostname: 'cache-prod-05', environment: 'PROD', vcpu_count: 8, memory_mb: 65536 },
  { id: 'sample-host-4', hostname: 'batch-etl-01', environment: 'STAGING', vcpu_count: 16, memory_mb: 32768 },
  { id: 'sample-host-5', hostname: 'api-staging-02', environment: 'STAGING', vcpu_count: 8, memory_mb: 16384 },
  { id: 'sample-host-6', hostname: 'batch-dev-03', environment: 'DEV', vcpu_count: 4, memory_mb: 8192 },
];

function sampleForecast(hostId) {
  return {
    id: 'sample-forecast',
    host_id: hostId,
    metric: 'CPU',
    generated_at: '2024-01-03T00:00:00Z',
    horizon_minutes: 60,
    model: 'STL_HOLTWINTERS',
    predicted_value: 16.0,
    lower_bound: 9.4,
    upper_bound: 22.6,
    mape: 11.3,
  };
}

function sampleRecommendation(host) {
  const recVcpu = Math.max(1, Math.floor(host.vcpu_count / 2));
  const recMem = Math.max(256, Math.floor(host.memory_mb / 2));
  const saving = Math.round(((host.vcpu_count - recVcpu) / host.vcpu_count) * 50 +
    ((host.memory_mb - recMem) / host.memory_mb) * 50);
  return {
    id: 'sample-rec',
    host_id: host.id,
    generated_at: '2024-01-03T00:00:00Z',
    current_vcpu: host.vcpu_count,
    recommended_vcpu: recVcpu,
    current_memory_mb: host.memory_mb,
    recommended_memory_mb: recMem,
    est_cost_saving_pct: saving,
    slo_confidence: 99.9,
    current_machine_type: nearestMachineType(host.vcpu_count, host.memory_mb),
    recommended_machine_type: nearestMachineType(recVcpu, recMem),
  };
}

// Retry transient failures (notably Cloud Run cold-start) before falling back to
// demo data, so a scale-to-zero backend still shows live data on first load. Each
// attempt has its own timeout so a stalled connection fails fast and is retried,
// and the window is wide enough (≈ up to ~45s) to absorb a cold container boot.
async function tryFetch(path, options, retries = 6) {
  if (!BASE_URL) throw new Error('no backend configured');
  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 8000);
    try {
      const resp = await fetch(`${BASE_URL}${path}`, { ...options, signal: ctrl.signal });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return await resp.json();
    } catch (e) {
      lastErr = e;
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, Math.min(2000, 600 * (attempt + 1))));
      }
    } finally {
      clearTimeout(timer);
    }
  }
  throw lastErr;
}

export async function fetchHosts() {
  try {
    const hosts = await tryFetch('/api/v1/hosts');
    return { hosts, live: true };
  } catch {
    return { hosts: SAMPLE_HOSTS, live: false };
  }
}

export async function fetchMachineTypes() {
  try {
    const types = await tryFetch('/api/v1/machine-types');
    return { types, live: true };
  } catch {
    return { types: SAMPLE_MACHINE_TYPES, live: false };
  }
}

export async function fetchMetrics(host) {
  try {
    const metrics = await tryFetch(`/api/v1/hosts/${host.id}/metrics`);
    return { metrics, live: true };
  } catch {
    const offset = SAMPLE_HOSTS.findIndex((h) => h.id === host.id) * 5;
    return { metrics: sampleSeries(Math.max(0, offset)), live: false };
  }
}

export async function fetchForecast(host, { log = false } = {}) {
  try {
    const forecast = await tryFetch(
      `/api/v1/hosts/${host.id}/forecast?metric=CPU&horizon_minutes=60&log=${log}`,
      { method: 'POST' },
    );
    return { forecast, live: true };
  } catch {
    return { forecast: sampleForecast(host.id), live: false };
  }
}

export async function fetchRecommendation(host) {
  try {
    const recommendation = await tryFetch(
      `/api/v1/hosts/${host.id}/recommendation`,
      { method: 'POST' },
    );
    return { recommendation, live: true };
  } catch {
    return { recommendation: sampleRecommendation(host), live: false };
  }
}

// In-memory action log used only by the demo fallback (no backend reachable).
const demoActions = {};

export async function applyResize(host, vcpuCount, memoryMb) {
  try {
    const updated = await tryFetch(`/api/v1/hosts/${host.id}/resize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vcpu_count: vcpuCount, memory_mb: memoryMb }),
    });
    return { host: updated, live: true };
  } catch {
    const saving = Math.round(
      (((host.vcpu_count - vcpuCount) / host.vcpu_count +
        (host.memory_mb - memoryMb) / host.memory_mb) /
        2) *
        100,
    );
    const verb = saving > 0 ? 'Downsized' : saving < 0 ? 'Upsized' : 'Kept';
    (demoActions[host.id] ||= []).unshift({
      id: `${Date.now()}`,
      action_type: 'RESIZE',
      detail: `${verb} ${host.hostname}: ${host.vcpu_count}->${vcpuCount} vCPU, ${
        host.memory_mb / 1024
      }->${memoryMb / 1024} GB (${saving > 0 ? '+' : ''}${saving}% capacity)`,
      saving_pct: saving,
      ts: new Date().toISOString(),
    });
    return {
      host: { ...host, vcpu_count: vcpuCount, memory_mb: memoryMb },
      live: false,
    };
  }
}

export async function fetchActions(host) {
  try {
    const actions = await tryFetch(`/api/v1/hosts/${host.id}/actions`);
    return { actions, live: true };
  } catch {
    return { actions: demoActions[host.id] || [], live: false };
  }
}

// Fleet-wide audit log across every host (newest first) — for the History view.
export async function fetchAllActions(limit = 200) {
  try {
    const actions = await tryFetch(`/api/v1/actions?limit=${limit}`);
    return { actions, live: true };
  } catch {
    const merged = Object.values(demoActions).flat();
    merged.sort((a, b) => (a.ts < b.ts ? 1 : -1));
    return { actions: merged.slice(0, limit), live: false };
  }
}

// Liveness/readiness probe used by the Test Scenarios view.
export async function checkHealth() {
  const probe = async (path) => {
    const t0 = Date.now();
    try {
      const r = await fetch(`${BASE_URL}${path}`);
      return { ok: r.ok, status: r.status, ms: Date.now() - t0 };
    } catch {
      return { ok: false, status: 0, ms: Date.now() - t0 };
    }
  };
  if (!BASE_URL) {
    return { live: false, health: { ok: true, status: 200, ms: 0 }, db: { ok: true, status: 200, ms: 0 } };
  }
  const [health, db] = await Promise.all([probe('/health'), probe('/health/db')]);
  return { live: true, health, db };
}

// Backtest the model vs naive baselines + interval coverage for a host.
export async function fetchEvaluation(host) {
  return tryFetch(`/api/v1/hosts/${host.id}/evaluation`, { method: 'POST' });
}

// --- Real GCP fleet (Cloud Monitoring ingestion + real VM resize) ---

export async function syncGcp() {
  try {
    const hosts = await tryFetch('/api/v1/gcp/sync', { method: 'POST' });
    return { hosts, live: true };
  } catch (e) {
    return { hosts: [], live: false, error: String(e.message || e) };
  }
}

export async function fetchGcpInstances() {
  try {
    return { instances: await tryFetch('/api/v1/gcp/instances'), live: true };
  } catch {
    return { instances: [], live: false };
  }
}

// --- On-demand scale-out test node (demo) ---
async function gcpAction(path, method) {
  const resp = await fetch(`${BASE_URL}${path}`, { method });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try { detail = (await resp.json()).detail || detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return resp.json();
}
export const launchTestNode = () => gcpAction('/api/v1/gcp/testnode', 'POST');
export const testNodeStatus = () => gcpAction('/api/v1/gcp/testnode', 'GET');
export const deleteTestNode = () => gcpAction('/api/v1/gcp/testnode', 'DELETE');

// Resize the real GCE VM behind a host. Surfaces the backend's error detail
// (e.g. budget-guard 402) as the thrown message.
export async function applyRealResize(host, machineType) {
  const resp = await fetch(
    `${BASE_URL}/api/v1/gcp/hosts/${host.id}/resize?machine_type=${encodeURIComponent(machineType)}`,
    { method: 'POST' },
  );
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      detail = (await resp.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return { host: await resp.json() };
}

// Original (seed) size for a hostname, used by the "reset fleet" scenario.
export function originalSizeFor(hostname) {
  const h = SAMPLE_HOSTS.find((s) => s.hostname === hostname);
  return h ? { vcpu_count: h.vcpu_count, memory_mb: h.memory_mb } : null;
}

// --- Live scale-out test (demo) -------------------------------------------
// Mirrors backend app/core/livetest.py so the animated demo still runs when no
// backend is configured (offline preview / screenshots). When a backend is up,
// the real endpoints drive it (and persist a Host + Metrics + Actions).
const LT = {
  T_RUNNING: 3, T_LOAD: 5, T_FORECAST: 11, T_SCALE: 13, T_RESIZING: 1.6, T_DONE: 24,
  SEC_PER_MIN: 0.5, THRESHOLD: 65, BASE: 12, PEAK: 93, POSTCPU: 44,
  PRE: { machine_type: 'e2-small', vcpu: 2, memory_mb: 2048 },
  POST: { machine_type: 'e2-standard-4', vcpu: 4, memory_mb: 16384 },
};
const ltNoise = (t) => 2.2 * Math.sin(t * 1.7) + 1.3 * Math.sin(t * 0.7 + 1);
function ltCpu(e) {
  let v;
  if (e < LT.T_LOAD) v = LT.BASE + ltNoise(e);
  else if (e < LT.T_SCALE) {
    v = LT.BASE + (LT.PEAK - LT.BASE) * ((e - LT.T_LOAD) / (LT.T_SCALE - LT.T_LOAD)) + ltNoise(e);
  } else v = LT.POSTCPU + (LT.PEAK - LT.POSTCPU) * Math.exp(-(e - LT.T_SCALE) / 3) + ltNoise(e);
  return Math.round(Math.max(0, Math.min(100, v)) * 10) / 10;
}
function ltPhase(e) {
  if (e < LT.T_RUNNING) return 'provisioning';
  if (e < LT.T_LOAD) return 'running';
  if (e < LT.T_FORECAST) return 'load';
  if (e < LT.T_SCALE) return 'forecast';
  if (e < LT.T_DONE) return 'scaling';
  return 'done';
}
function ltStatus(e) {
  if (e < LT.T_RUNNING) return 'PROVISIONING';
  if (e >= LT.T_SCALE && e < LT.T_SCALE + LT.T_RESIZING) return 'RESIZING';
  return 'RUNNING';
}
function ltSimulate(elapsed, mode) {
  const e = Math.max(0, elapsed);
  const scaled = e >= LT.T_SCALE;
  const done = e >= LT.T_DONE;
  const spec = scaled ? LT.POST : LT.PRE;
  const series = [];
  if (e >= LT.T_RUNNING) {
    const end = Math.min(e, LT.T_DONE);
    for (let t = LT.T_RUNNING; t <= end + 1e-9; t += 0.5) {
      series.push([Math.round((t / LT.SEC_PER_MIN) * 10) / 10, ltCpu(t)]);
    }
  }
  const ev = (t, kind, key) => ({ minute: Math.round((t / LT.SEC_PER_MIN) * 10) / 10, kind, key });
  const events = [];
  if (e >= LT.T_RUNNING) events.push(ev(LT.T_RUNNING, 'node', 'ev_running'));
  if (e >= LT.T_LOAD) events.push(ev(LT.T_LOAD, 'load', 'ev_load'));
  if (e >= LT.T_FORECAST) events.push(ev(LT.T_FORECAST, 'forecast', 'ev_forecast'));
  if (e >= LT.T_SCALE) events.push(ev(LT.T_SCALE, 'scale', 'ev_scale'));
  const forecast = e >= LT.T_FORECAST ? { predicted: 108, lower: 95, upper: 121, mape: 6.4 } : null;
  const recommendation = e >= LT.T_FORECAST ? {
    current_vcpu: LT.PRE.vcpu, recommended_vcpu: LT.POST.vcpu,
    current_memory_mb: LT.PRE.memory_mb, recommended_memory_mb: LT.POST.memory_mb,
    current_machine_type: LT.PRE.machine_type, recommended_machine_type: LT.POST.machine_type,
  } : null;
  return {
    active: true, mode, phase: ltPhase(e), threshold: LT.THRESHOLD,
    elapsed: Math.round(e * 100) / 100, scaled, done, cpu_now: series.length ? series[series.length - 1][1] : null,
    series, events, forecast, recommendation, spec, pre: LT.PRE, post: LT.POST,
    node: { hostname: mode === 'real' ? 'ml-testnode' : 'loadtest-sim-01', status: ltStatus(e), ...spec },
  };
}

let _ltT0 = null;
let _ltMode = 'sim';
async function ltOnce(path, method) {
  if (!BASE_URL) throw new Error('no backend');
  const resp = await fetch(`${BASE_URL}${path}`, method ? { method } : undefined);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}
export async function livetestStart(mode = 'sim') {
  try {
    return { ...(await ltOnce(`/api/v1/livetest/start?mode=${mode}`, 'POST')), live: true };
  } catch {
    _ltT0 = Date.now(); _ltMode = mode;
    return { ...ltSimulate(0, mode), live: false };
  }
}
export async function livetestState() {
  try {
    return { ...(await ltOnce('/api/v1/livetest/state')), live: true };
  } catch {
    if (_ltT0 == null) return { active: false, live: false };
    return { ...ltSimulate((Date.now() - _ltT0) / 1000, _ltMode), live: false };
  }
}
export async function livetestStop() {
  _ltT0 = null;
  try { return await ltOnce('/api/v1/livetest/stop', 'POST'); } catch { return { active: false }; }
}
export async function livetestTeardown() {
  _ltT0 = null;
  try { return await ltOnce('/api/v1/livetest/teardown', 'POST'); } catch { return { active: false, removed: true }; }
}
