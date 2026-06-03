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
