import { useCallback, useEffect, useRef, useState } from 'react';
import {
  applyResize,
  fetchActions,
  fetchForecast,
  fetchHosts,
  fetchMachineTypes,
  fetchMetrics,
  fetchRecommendation,
  nearestMachineType,
} from './api.js';
import MetricChart from './components/MetricChart.jsx';
import ForecastPanel from './components/ForecastPanel.jsx';
import RecommendationCard from './components/RecommendationCard.jsx';
import KpiStrip from './components/KpiStrip.jsx';
import Gauge from './components/Gauge.jsx';
import ResizeControls from './components/ResizeControls.jsx';
import ActivityLog from './components/ActivityLog.jsx';
import InfoTip from './components/InfoTip.jsx';
import NavBar from './components/NavBar.jsx';
import HistoryView from './views/HistoryView.jsx';
import TestsView from './views/TestsView.jsx';
import { GLOSSARY } from './glossary.js';
import './App.css';

export default function App() {
  const [hosts, setHosts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [metrics, setMetrics] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [actions, setActions] = useState([]);
  const [fleet, setFleet] = useState([]);
  const [machineTypes, setMachineTypes] = useState([]);
  const [live, setLive] = useState(true);
  const [busy, setBusy] = useState(false);
  const [baseline, setBaseline] = useState(1);
  const [view, setView] = useState('dashboard');

  // Capacity at which each host's metrics were measured, so projected
  // utilisation can be recomputed as the allocation is resized. Written/read
  // only inside effects (never during render).
  const baselines = useRef({});

  useEffect(() => {
    fetchMachineTypes().then(({ types }) => setMachineTypes(types));
  }, []);

  // Load (or reload) the fleet — preserving the current selection across the
  // mutations a Test Scenario may apply.
  const loadFleet = useCallback(async () => {
    const { hosts: list, live: isLive } = await fetchHosts();
    setHosts(list);
    setLive(isLive);
    list.forEach((h) => {
      baselines.current[h.id] ??= h.vcpu_count;
    });
    setSelected((cur) => {
      const same = cur && list.find((h) => h.id === cur.id);
      return same || list.find((h) => h.environment === 'PROD') || list[0] || null;
    });
    const results = await Promise.all(list.map((h) => fetchRecommendation(h)));
    setFleet(list.map((h, i) => ({ host: h, rec: results[i].recommendation })));
  }, []);

  useEffect(() => {
    // loadFleet only sets state after awaiting fetches (never synchronously),
    // so the cascading-render heuristic does not apply here.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadFleet();
  }, [loadFleet]);

  useEffect(() => {
    if (!selected) return;
    let active = true;
    baselines.current[selected.id] ??= selected.vcpu_count;
    setBaseline(baselines.current[selected.id]);
    Promise.all([
      fetchMetrics(selected),
      fetchForecast(selected, { log: false }),
      fetchRecommendation(selected),
      fetchActions(selected),
    ]).then(([m, f, r, a]) => {
      if (!active) return;
      setMetrics(m.metrics);
      setForecast(f.forecast);
      setRecommendation(r.recommendation);
      setActions(a.actions);
      setLive(m.live && f.live && r.live);
    });
    return () => {
      active = false;
    };
  }, [selected]);

  const peakCpu = metrics.length ? Math.max(...metrics.map((m) => m.cpu_pct)) : 0;
  const loadCores = (peakCpu / 100) * baseline;
  const projectedUtil = selected
    ? Math.min(100, (loadCores / selected.vcpu_count) * 100)
    : 0;

  function applyHostUpdate(updated) {
    setHosts((hs) => hs.map((h) => (h.id === updated.id ? updated : h)));
    setSelected(updated); // re-runs the loader effect to refresh everything
  }

  async function doResize(vcpu, memory) {
    if (!selected || busy) return;
    setBusy(true);
    const { host: updated } = await applyResize(selected, vcpu, memory);
    applyHostUpdate(updated);
    const r = await fetchRecommendation(updated);
    setFleet((fl) =>
      fl.map((f) =>
        f.host.id === updated.id ? { host: updated, rec: r.recommendation } : f,
      ),
    );
    setBusy(false);
  }

  async function runForecast() {
    if (!selected || busy) return;
    setBusy(true);
    const f = await fetchForecast(selected, { log: true });
    setForecast(f.forecast);
    const a = await fetchActions(selected);
    setActions(a.actions);
    setBusy(false);
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◧</span>
          <div>
            <h1>MetricLens AI</h1>
            <p>Time-series load forecasting &amp; resizing optimisation</p>
          </div>
        </div>
        <div className="topbar-right">
          <a className="deck-link" href="/presentation.html" target="_blank" rel="noreferrer">
            📊 Slides
          </a>
          <span className={`badge ${live ? 'live' : 'demo'}`}>
            {live ? '● live' : '● demo data'}
          </span>
        </div>
      </header>

      <NavBar view={view} onChange={setView} />

      {view === 'history' && <HistoryView hosts={hosts} />}
      {view === 'tests' && <TestsView hosts={hosts} onChanged={loadFleet} />}

      {view === 'dashboard' && (
        <>
          {fleet.length > 0 && <KpiStrip fleet={fleet} />}

          <nav className="host-tabs">
        {hosts.map((h) => (
          <button
            key={h.id}
            className={selected && h.id === selected.id ? 'tab active' : 'tab'}
            onClick={() => setSelected(h)}
          >
            <span className="host-name">{h.hostname}</span>
            <span className={`env env-${h.environment.toLowerCase()}`}>
              {h.environment}
            </span>
            <span className="host-spec">
              {h.vcpu_count} vCPU · {(h.memory_mb / 1024).toFixed(0)} GB
            </span>
            <span className="host-mtype">
              {h.provider === 'gce'
                ? `${h.machine_type || ''} · ☁ GCE`
                : nearestMachineType(h.vcpu_count, h.memory_mb, machineTypes.length ? machineTypes : undefined).name}
            </span>
          </button>
        ))}
      </nav>

      <main className="grid">
        <section className="panel chart-panel">
          {metrics.length > 0 && <MetricChart metrics={metrics} />}
        </section>
        <aside className="side">
          {metrics.length > 0 && selected && (
            <div className="panel">
              <h3>
                Projected Utilisation @ {selected.vcpu_count} vCPU
                <InfoTip text={GLOSSARY.projectedUtil} label="예상 가동률" />
              </h3>
              <Gauge value={projectedUtil} label="projected %" />
              <ResizeControls
                current={selected.vcpu_count}
                currentMemoryMb={selected.memory_mb}
                recommended={recommendation?.recommended_vcpu}
                util={projectedUtil}
                busy={busy}
                machineTypes={machineTypes}
                onSelectType={(t) => doResize(t.vcpu, t.memory_mb)}
                onScaleDown={() =>
                  doResize(
                    Math.max(1, Math.floor(selected.vcpu_count / 2)),
                    Math.max(256, Math.floor(selected.memory_mb / 2)),
                  )
                }
                onScaleUp={() =>
                  doResize(
                    Math.min(256, selected.vcpu_count * 2),
                    Math.min(4194304, selected.memory_mb * 2),
                  )
                }
                onApply={() =>
                  recommendation &&
                  doResize(
                    recommendation.recommended_vcpu,
                    recommendation.recommended_memory_mb,
                  )
                }
                onForecast={runForecast}
              />
            </div>
          )}
          {forecast && metrics.length > 0 && (
            <ForecastPanel metrics={metrics} forecast={forecast} />
          )}
          {recommendation && <RecommendationCard recommendation={recommendation} />}
          <ActivityLog actions={actions} />
        </aside>
      </main>
        </>
      )}

      <footer className="footer">
        MetricLens AI · lightweight CPU-only forecasting · target MAPE ≤ 15% ·
        SLO 99.9%
      </footer>
    </div>
  );
}
