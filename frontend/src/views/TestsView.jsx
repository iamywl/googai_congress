import { useState } from 'react';
import {
  applyRealResize,
  applyResize,
  checkHealth,
  fetchEvaluation,
  fetchForecast,
  fetchRecommendation,
  originalSizeFor,
  syncGcp,
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
      id: 'evaluate',
      label: '📊 Evaluate model vs baselines',
      desc: '각 호스트에서 모델을 naive·seasonal-naive 기준선과 백테스트 비교하고 95% 예측구간 커버리지를 측정합니다.',
      fn: async () => {
        const rows = [];
        for (const host of hosts) {
          try {
            const e = await fetchEvaluation(host);
            const beats = e.beats_seasonal_naive && e.beats_naive ? 'beats both' :
              e.beats_seasonal_naive ? 'beats s-naive' : 'no';
            rows.push({
              label: host.hostname,
              value: `MAPE ${e.model.mape}% vs s-naive ${e.seasonal_naive.mape}% · cover ${e.coverage} · ${beats}`,
              ok: e.beats_seasonal_naive,
            });
          } catch (err) {
            rows.push({ label: host.hostname, value: String(err.message || err), ok: false });
          }
        }
        return {
          title: '모델 평가 (백테스트 vs 기준선)',
          rows,
          note: 'ok = 모델 RMSE ≤ seasonal-naive. 커버리지는 0.95에 가까울수록 보정 양호.',
        };
      },
    },
    {
      id: 'gcpsync',
      label: '🔄 Sync real GCP fleet',
      desc: '라벨된 실제 GCE 인스턴스(ml-*)의 CPU를 Cloud Monitoring에서 가져와 호스트로 등록합니다.',
      fn: async () => {
        const { hosts: synced, error } = await syncGcp();
        if (error) {
          return { title: 'GCP sync', rows: [{ label: 'error', value: error, ok: false }], note: '백엔드 GCP 권한/배포를 확인하세요.' };
        }
        return {
          title: `실제 GCE 인스턴스 ${synced.length}개 동기화`,
          rows: synced.map((h) => ({
            label: h.hostname,
            value: `${h.machine_type || ''} · ${h.vcpu_count} vCPU / ${(h.memory_mb / 1024).toFixed(0)} GB`,
            ok: true,
          })),
          note: 'Cloud Monitoring 실측 CPU가 적재됨(메모리는 에이전트 미설치로 프록시).',
        };
      },
    },
    {
      id: 'realresize',
      label: '🧪 Real resize: idle VM → e2-micro',
      desc: '유휴 실제 VM을 e2-micro로 실제 리사이즈(stop→변경→start). 월 ₩300k 비용 가드.',
      fn: async () => {
        const { hosts: synced } = await syncGcp();
        const target = synced.find((h) => h.hostname.includes('idle')) ||
          synced.find((h) => h.provider === 'gce');
        if (!target) {
          return { title: 'Real resize', rows: [{ label: 'no real host', value: '먼저 GCP sync 필요', ok: false }] };
        }
        try {
          const { host } = await applyRealResize(target, 'e2-micro');
          return {
            title: 'Real resize 적용됨',
            rows: [{ label: host.hostname, value: `→ ${host.machine_type} (${host.vcpu_count} vCPU / ${(host.memory_mb / 1024).toFixed(0)} GB)`, ok: true }],
            note: '실제 VM이 stop→머신타입 변경→start 되었습니다(다운타임 ~1분).',
          };
        } catch (e) {
          return { title: 'Real resize', rows: [{ label: target.hostname, value: String(e.message || e), ok: false }], note: '비용 가드 또는 오류로 미적용.' };
        }
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
