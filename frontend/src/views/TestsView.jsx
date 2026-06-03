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
import { glossary } from '../glossary.js';
import { useT } from '../i18n.jsx';

// Runnable test/demo scenarios. Each button executes a real end-to-end flow
// against the backend and renders a result table, so the predict → resize loop
// can be exercised and inspected on demand.
export default function TestsView({ hosts, onChanged }) {
  const { t, lang } = useT();
  const GL = glossary(lang);
  const L = (en, ko) => (lang === 'ko' ? ko : en);
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
      label: L('🩺 Health check', '🩺 헬스 체크'),
      desc: L('Checks backend liveness (/health) and readiness (/health/db).',
        '백엔드 liveness(/health)와 readiness(/health/db)를 점검합니다.'),
      fn: async () => {
        const h = await checkHealth();
        return {
          title: L('Backend health', '백엔드 헬스'),
          rows: [
            { label: '/health (liveness)', value: h.health.ok ? `OK · ${h.health.ms}ms` : `FAIL (${h.health.status})`, ok: h.health.ok },
            { label: '/health/db (readiness)', value: h.db.ok ? `OK · ${h.db.ms}ms` : `FAIL (${h.db.status})`, ok: h.db.ok },
          ],
          note: h.live ? L('Live backend responded.', '라이브 백엔드 응답.')
            : L('Demo mode (backend not connected).', '데모 모드(백엔드 미연결).'),
        };
      },
    },
    {
      id: 'forecast',
      label: L('🔮 Run forecast on all hosts', '🔮 전 호스트 예측 실행'),
      desc: L('Runs a +60m CPU forecast on every host and shows MAPE (target ≤ 15%).',
        '모든 호스트에 +60분 CPU 예측을 실행하고 MAPE(≤15% 목표)를 표시합니다.'),
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
        return { title: L('Forecast — all hosts', '예측 — 전 호스트'), rows,
          note: L('ok = meets the 15% MAPE target.', 'ok = MAPE 15% 목표 충족.') };
      },
    },
    {
      id: 'optimize',
      label: L('🎯 Optimize fleet (apply AI recommendation)', '🎯 플릿 최적화 (AI 권장 적용)'),
      desc: L('Applies the AI recommendation to each host for real and shows the saving.',
        '각 호스트에 AI 권장 사양을 실제 적용(영속)하고 절감률을 표시합니다.'),
      fn: async () => {
        const rows = [];
        for (const host of hosts) {
          const { recommendation: r } = await fetchRecommendation(host);
          const changed = r.recommended_vcpu !== host.vcpu_count || r.recommended_memory_mb !== host.memory_mb;
          if (changed) await applyResize(host, r.recommended_vcpu, r.recommended_memory_mb);
          rows.push({
            label: host.hostname,
            value: `${host.vcpu_count}→${r.recommended_vcpu} vCPU · saving ${r.est_cost_saving_pct.toFixed(0)}%`,
            ok: r.est_cost_saving_pct > 0 || !changed,
          });
        }
        return { title: L('Fleet optimisation applied', '플릿 최적화 적용됨'), rows,
          note: L('Resized to the recommended spec (logged to the activity log).',
            '권장 사양으로 실제 리사이즈됨(활동 로그에 기록).') };
      },
    },
    {
      id: 'evaluate',
      label: L('📊 Evaluate model vs baselines', '📊 모델 vs 기준선 평가'),
      desc: L('Backtests the model against naive & seasonal-naive baselines and measures 95% interval coverage per host.',
        '각 호스트에서 모델을 naive·seasonal-naive 기준선과 백테스트 비교하고 95% 예측구간 커버리지를 측정합니다.'),
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
          title: L('Model evaluation (backtest vs baselines)', '모델 평가 (백테스트 vs 기준선)'),
          rows,
          note: L('ok = model RMSE ≤ seasonal-naive. Coverage near 0.95 = well-calibrated.',
            'ok = 모델 RMSE ≤ seasonal-naive. 커버리지는 0.95에 가까울수록 보정 양호.'),
        };
      },
    },
    {
      id: 'gcpsync',
      label: L('🔄 Sync real GCP fleet', '🔄 실제 GCP 플릿 동기화'),
      desc: L('Ingests labelled real GCE instances (ml-*) CPU from Cloud Monitoring as hosts.',
        '라벨된 실제 GCE 인스턴스(ml-*)의 CPU를 Cloud Monitoring에서 가져와 호스트로 등록합니다.'),
      fn: async () => {
        const { hosts: synced, error } = await syncGcp();
        if (error) {
          return { title: 'GCP sync', rows: [{ label: 'error', value: error, ok: false }],
            note: L('Check backend GCP permissions/deploy.', '백엔드 GCP 권한/배포를 확인하세요.') };
        }
        return {
          title: L(`Synced ${synced.length} real GCE instances`, `실제 GCE 인스턴스 ${synced.length}개 동기화`),
          rows: synced.map((h) => ({
            label: h.hostname,
            value: `${h.machine_type || ''} · ${h.vcpu_count} vCPU / ${(h.memory_mb / 1024).toFixed(0)} GB`,
            ok: true,
          })),
          note: L('Real CPU ingested from Cloud Monitoring (memory is a proxy until the agent reports).',
            'Cloud Monitoring 실측 CPU가 적재됨(메모리는 에이전트 보고 전까지 프록시).'),
        };
      },
    },
    {
      id: 'realresize',
      label: L('🧪 Real resize: idle VM → e2-micro', '🧪 실제 리사이즈: 유휴 VM → e2-micro'),
      desc: L('Really resizes an idle VM to e2-micro (stop→change→start). Guarded by the ≤300k KRW/month budget.',
        '유휴 실제 VM을 e2-micro로 실제 리사이즈(stop→변경→start). 월 ₩300k 비용 가드.'),
      fn: async () => {
        const { hosts: synced } = await syncGcp();
        const target = synced.find((h) => h.hostname.includes('idle')) ||
          synced.find((h) => h.provider === 'gce');
        if (!target) {
          return { title: 'Real resize', rows: [{ label: 'no real host',
            value: L('sync GCP first', '먼저 GCP sync 필요'), ok: false }] };
        }
        try {
          const { host } = await applyRealResize(target, 'e2-micro');
          return {
            title: L('Real resize applied', '실제 리사이즈 적용됨'),
            rows: [{ label: host.hostname, value: `→ ${host.machine_type} (${host.vcpu_count} vCPU / ${(host.memory_mb / 1024).toFixed(0)} GB)`, ok: true }],
            note: L('The real VM was stopped → machine-type changed → started (~1 min downtime).',
              '실제 VM이 stop→머신타입 변경→start 되었습니다(다운타임 ~1분).'),
          };
        } catch (e) {
          return { title: 'Real resize', rows: [{ label: target.hostname, value: String(e.message || e), ok: false }],
            note: L('Not applied (budget guard or error).', '비용 가드 또는 오류로 미적용.') };
        }
      },
    },
    {
      id: 'reset',
      label: L('↺ Reset fleet to original sizes', '↺ 플릿 원래 사양 복원'),
      desc: L('Restores every host to its original seed spec.', '모든 호스트를 최초 시드 사양으로 되돌립니다.'),
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
        return { title: L('Fleet reset', '플릿 복원'), rows,
          note: L('Restored to the original seed spec.', '최초 시드 사양으로 복원됨.') };
      },
    },
  ];

  return (
    <div className="tests">
      <section className="panel">
        <h3>
          {t('tvTitle')}
          <InfoTip text={GL.activityLog} label={t('tvTitle')} />
        </h3>
        <p className="rec-note">{t('tvDesc')}</p>
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
              {running === s.id && <span className="scenario-running">{t('tvRunning')}</span>}
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
