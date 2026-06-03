import { useState } from 'react';
import {
  applyResize,
  checkHealth,
  fetchForecast,
  fetchRecommendation,
  originalSizeFor,
} from '../api.js';
import InfoTip from '../components/InfoTip.jsx';
import { GLOSSARY } from '../glossary.js';

// Runnable test/demo scenarios. Each button executes a real end-to-end flow
// against the backend and renders a result table, so the predict → resize loop
// can be exercised and inspected on demand.
export default function TestsView({ hosts, onChanged }) {
  const [running, setRunning] = useState(null);
  const [result, setResult] = useState(null);

  async function run(id, fn) {
    setRunning(id);
    setResult(null);
    try {
      setResult(await fn());
    } catch (e) {
      setResult({ title: 'Error', error: String(e), rows: [] });
    } finally {
      setRunning(null);
      onChanged?.();
    }
  }

  const scenarios = [
    {
      id: 'health',
      label: '🩺 Health check',
      desc: '백엔드 liveness(/health)와 readiness(/health/db)를 점검합니다.',
      fn: async () => {
        const h = await checkHealth();
        return {
          title: 'Backend health',
          rows: [
            { label: '/health (liveness)', value: h.health.ok ? `OK · ${h.health.ms}ms` : `FAIL (${h.health.status})`, ok: h.health.ok },
            { label: '/health/db (readiness)', value: h.db.ok ? `OK · ${h.db.ms}ms` : `FAIL (${h.db.status})`, ok: h.db.ok },
          ],
          note: h.live ? '라이브 백엔드 응답.' : '데모 모드(백엔드 미연결).',
        };
      },
    },
    {
      id: 'forecast',
      label: '🔮 Run forecast on all hosts',
      desc: '모든 호스트에 +60분 CPU 예측을 실행하고 MAPE(≤15% 목표)를 표시합니다.',
      fn: async () => {
        const rows = [];
        for (const host of hosts) {
          const { forecast: f } = await fetchForecast(host, { log: true });
          const ok = f.mape != null && f.mape <= 15;
          rows.push({
            label: host.hostname,
            value: `pred ${f.predicted_value.toFixed(0)}% · MAPE ${f.mape == null ? 'n/a' : f.mape.toFixed(1) + '%'}`,
            ok,
          });
        }
        return { title: 'Forecast — all hosts', rows, note: 'ok = MAPE 15% 목표 충족.' };
      },
    },
    {
      id: 'optimize',
      label: '🎯 Optimize fleet (apply AI recommendation)',
      desc: '각 호스트에 AI 권장 사양을 실제 적용(영속)하고 절감률을 표시합니다.',
      fn: async () => {
        const rows = [];
        for (const host of hosts) {
          const { recommendation: r } = await fetchRecommendation(host);
          const changed = r.recommended_vcpu !== host.vcpu_count || r.recommended_memory_mb !== host.memory_mb;
          if (changed) {
            await applyResize(host, r.recommended_vcpu, r.recommended_memory_mb);
          }
          rows.push({
            label: host.hostname,
            value: `${host.vcpu_count}→${r.recommended_vcpu} vCPU · saving ${r.est_cost_saving_pct.toFixed(0)}%`,
            ok: r.est_cost_saving_pct > 0 || !changed,
          });
        }
        return { title: 'Fleet optimisation applied', rows, note: '권장 사양으로 실제 리사이즈됨(활동 로그에 기록).' };
      },
    },
    {
      id: 'reset',
      label: '↺ Reset fleet to original sizes',
      desc: '모든 호스트를 최초 시드 사양으로 되돌립니다.',
      fn: async () => {
        const rows = [];
        for (const host of hosts) {
          const orig = originalSizeFor(host.hostname);
          if (!orig) {
            rows.push({ label: host.hostname, value: 'no baseline', ok: false });
            continue;
          }
          const changed = orig.vcpu_count !== host.vcpu_count || orig.memory_mb !== host.memory_mb;
          if (changed) await applyResize(host, orig.vcpu_count, orig.memory_mb);
          rows.push({
            label: host.hostname,
            value: `→ ${orig.vcpu_count} vCPU / ${(orig.memory_mb / 1024).toFixed(0)} GB`,
            ok: true,
          });
        }
        return { title: 'Fleet reset', rows, note: '최초 시드 사양으로 복원됨.' };
      },
    },
  ];

  return (
    <div className="tests">
      <section className="panel">
        <h3>
          Test Scenarios
          <InfoTip text={GLOSSARY.activityLog} label="테스트" />
        </h3>
        <p className="rec-note">
          버튼을 누르면 실제 백엔드에 대해 시나리오가 실행됩니다. 예측·리사이즈는 영속
          기록되어 Dashboard와 History에 즉시 반영됩니다.
        </p>
        <div className="scenario-grid">
          {scenarios.map((s) => (
            <button
              key={s.id}
              className="scenario-btn"
              disabled={running != null}
              onClick={() => run(s.id, s.fn)}
            >
              <span className="scenario-label">{s.label}</span>
              <span className="scenario-desc">{s.desc}</span>
              {running === s.id && <span className="scenario-running">실행 중…</span>}
            </button>
          ))}
        </div>
      </section>

      {result && (
        <section className="panel">
          <h3>{result.title}</h3>
          {result.error && <p className="warn">{result.error}</p>}
          <table className="data-table">
            <tbody>
              {result.rows.map((r, i) => (
                <tr key={i}>
                  <td>{r.label}</td>
                  <td className={r.ok === false ? 'warn' : r.ok === true ? 'good' : ''}>
                    {r.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {result.note && <p className="rec-note">{result.note}</p>}
        </section>
      )}
    </div>
  );
}
