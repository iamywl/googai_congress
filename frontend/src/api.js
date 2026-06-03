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

export const SAMPLE_HOSTS = [
  { id: 'sample-host-1', hostname: 'web-prod-01', environment: 'PROD', vcpu_count: 16, memory_mb: 32768 },
  { id: 'sample-host-2', hostname: 'api-staging-02', environment: 'STAGING', vcpu_count: 8, memory_mb: 16384 },
  { id: 'sample-host-3', hostname: 'batch-dev-03', environment: 'DEV', vcpu_count: 4, memory_mb: 8192 },
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
  };
}

async function tryFetch(path, options) {
  if (!BASE_URL) throw new Error('no backend configured');
  const resp = await fetch(`${BASE_URL}${path}`, options);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

export async function fetchHosts() {
  try {
    const hosts = await tryFetch('/api/v1/hosts');
    return { hosts, live: true };
  } catch {
    return { hosts: SAMPLE_HOSTS, live: false };
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
