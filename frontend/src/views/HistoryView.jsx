import { useEffect, useMemo, useState } from 'react';
import { fetchAllActions, fetchMetrics } from '../api.js';
import InfoTip from '../components/InfoTip.jsx';
import { glossary } from '../glossary.js';
import { useT } from '../i18n.jsx';

// Full history browser: a fleet-wide audit log plus the complete metric history
// for any selected host, so every past prediction, resize, and measurement can
// be read end to end.
export default function HistoryView({ hosts }) {
  const { t, lang } = useT();
  const GL = glossary(lang);
  const [actions, setActions] = useState([]);
  const [picked, setPicked] = useState(null);
  const [metrics, setMetrics] = useState(null);

  // The effective host is derived (no setState-in-effect): the user's pick if
  // any, otherwise the first host once the fleet loads.
  const selected = picked || hosts[0] || null;

  useEffect(() => {
    fetchAllActions(500).then(({ actions: a }) => setActions(a));
  }, []);

  useEffect(() => {
    if (!selected) return;
    let active = true;
    fetchMetrics(selected).then(({ metrics: m }) => {
      if (active) setMetrics(m);
    });
    return () => {
      active = false;
    };
  }, [selected]);
  const loading = metrics === null;

  const stats = useMemo(() => {
    if (!metrics || !metrics.length) return null;
    const cpu = metrics.map((m) => m.cpu_pct);
    const mem = metrics.map((m) => m.mem_pct);
    const avg = (a) => Math.round(a.reduce((s, v) => s + v, 0) / a.length);
    return {
      samples: metrics.length,
      cpuAvg: avg(cpu), cpuMax: Math.max(...cpu),
      memAvg: avg(mem), memMax: Math.max(...mem),
      from: metrics[0].ts, to: metrics[metrics.length - 1].ts,
    };
  }, [metrics]);

  const fmt = (ts) => (ts ? ts.replace('T', ' ').slice(0, 16) : '');

  return (
    <div className="history">
      <section className="panel">
        <h3>
          {t('hvFleetLog')}
          <InfoTip text={GL.activityLog} label={t('hvFleetLog')} />
        </h3>
        <p className="rec-note">{t('hvFleetDesc')}</p>
        {actions.length === 0 ? (
          <p className="rec-note">{t('hvEmpty')}</p>
        ) : (
          <ul className="log tall">
            {actions.map((a) => (
              <li key={a.id} className={`log-item ${a.action_type.toLowerCase()}`}>
                <span className="log-tag">{a.action_type}</span>
                <div className="log-body">
                  <span className="log-detail">{a.detail}</span>
                  <span className="log-meta">
                    {fmt(a.ts)}
                    {a.saving_pct != null && a.saving_pct > 0 && (
                      <em className="log-saving">−{a.saving_pct}% {t('alCapacity')}</em>
                    )}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h3>{t('hvMetricHistory')}</h3>
        <div className="history-hosts">
          {hosts.map((h) => (
            <button
              key={h.id}
              className={`chip-btn ${selected && selected.id === h.id ? 'active' : ''}`}
              onClick={() => setPicked(h)}
            >
              {h.hostname}
            </button>
          ))}
        </div>

        {stats && (
          <div className="history-stats">
            <span>{t('hvSamples')} <strong>{stats.samples}</strong></span>
            <span>{t('hvPeriod')} <strong>{fmt(stats.from)} ~ {fmt(stats.to)}</strong></span>
            <span>{t('hvCpuAvgMax')} <strong>{stats.cpuAvg}% / {stats.cpuMax}%</strong></span>
            <span>{t('hvMemAvgMax')} <strong>{stats.memAvg}% / {stats.memMax}%</strong></span>
          </div>
        )}

        <div className="table-wrap">
          {loading ? (
            <p className="rec-note">{t('hvLoading')}</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('thTimestamp')}</th>
                  <th>CPU %</th>
                  <th>Memory %</th>
                  <th>Net In (kbps)</th>
                  <th>Net Out (kbps)</th>
                </tr>
              </thead>
              <tbody>
                {[...(metrics || [])].reverse().map((m, i) => (
                  <tr key={`${m.ts}-${i}`}>
                    <td>{fmt(m.ts)}</td>
                    <td>{Math.round(m.cpu_pct)}</td>
                    <td>{Math.round(m.mem_pct)}</td>
                    <td>{Math.round(m.net_in_kbps)}</td>
                    <td>{Math.round(m.net_out_kbps)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
