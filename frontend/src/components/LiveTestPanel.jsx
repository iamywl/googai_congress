import { useCallback, useEffect, useRef, useState } from 'react';
import { livetestStart, livetestState, livetestStop, livetestTeardown } from '../api.js';
import { useT } from '../i18n.jsx';
import EChart from './EChart.jsx';

const STEP_KEYS = [
  'ltStepProvision', 'ltStepLoad', 'ltStepBreach',
  'ltStepForecast', 'ltStepScale', 'ltStepStable',
];

function activeStep(st) {
  if (!st || !st.active) return -1;
  switch (st.phase) {
    case 'provisioning': return 0;
    case 'running': return 1;
    case 'load': return (st.cpu_now ?? 0) > st.threshold ? 2 : 1;
    case 'forecast': return 3;
    case 'scaling': return st.done ? 5 : 4;
    case 'done': return 5;
    default: return 0;
  }
}

function chartOption(st, t) {
  const series = st?.series || [];
  const threshold = st?.threshold ?? 65;
  const scaleMin = st?.scaled ? 13 / 0.5 : null;       // T_SCALE / SEC_PER_MIN
  const markLineData = [
    { yAxis: threshold, label: { formatter: `${t('ltThreshold')} ${threshold}%`, position: 'insideEndTop', color: '#c07d0a' },
      lineStyle: { color: '#c07d0a', type: 'dashed' } },
  ];
  if (scaleMin != null) {
    markLineData.push({
      xAxis: scaleMin, label: { formatter: t('ev_scale'), color: '#1a9850', position: 'insideEndBottom' },
      lineStyle: { color: '#1a9850', width: 1.5 },
    });
  }
  const markPoint = st?.forecast ? {
    symbolSize: 1, label: { show: true, formatter: `▲ ${t('ltForecast')} ~${Math.round(st.forecast.predicted)}%`, color: '#d23b3b', fontWeight: 600 },
    data: [{ coord: [st.forecast ? 11 / 0.5 : 0, 100], value: '' }],
  } : undefined;
  return {
    grid: { left: 44, right: 16, top: 22, bottom: 34 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value', name: t('ltMinutes'), nameLocation: 'middle', nameGap: 22, min: 0, max: 48 },
    yAxis: { type: 'value', name: t('ltCpu'), min: 0, max: 100 },
    series: [{
      name: t('ltCpu'), type: 'line', smooth: true, showSymbol: false,
      data: series, lineStyle: { width: 2.4, color: '#3274d9' },
      areaStyle: { color: 'rgba(50,116,217,0.10)' },
      markLine: { symbol: 'none', data: markLineData },
      markPoint,
    }],
  };
}

export default function LiveTestPanel({ onChanged }) {
  const { t } = useT();
  const [mode, setMode] = useState('sim');
  const [st, setSt] = useState(null);
  const [running, setRunning] = useState(false);
  const timer = useRef(null);
  const scaledSeen = useRef(false);

  const stopPolling = useCallback(() => {
    if (timer.current) { clearInterval(timer.current); timer.current = null; }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  async function run() {
    if (running) return;
    scaledSeen.current = false;
    setRunning(true);
    const first = await livetestStart(mode);
    setSt(first);
    onChanged?.();
    stopPolling();
    timer.current = setInterval(async () => {
      const s = await livetestState();
      setSt(s);
      if (s.scaled && !scaledSeen.current) { scaledSeen.current = true; onChanged?.(); }
      if (!s.active || s.done) {
        stopPolling();
        setRunning(false);
        onChanged?.();
      }
    }, 1000);
  }

  async function stop() {
    stopPolling();
    setRunning(false);
    await livetestStop();
    setSt((s) => (s ? { ...s, active: false } : s));
  }

  async function teardown() {
    stopPolling();
    setRunning(false);
    await livetestTeardown();
    setSt(null);
    onChanged?.();
  }

  const step = activeStep(st);
  const node = st?.node;
  const gb = (mb) => (mb / 1024).toFixed(0);

  return (
    <section className="panel livetest">
      <div className="lt-head">
        <div>
          <h3>{t('ltTitle')}</h3>
          <p className="lt-desc">{t('ltDesc')}</p>
        </div>
        <div className="lt-controls">
          <div className="lt-modes">
            <button className={mode === 'sim' ? 'on' : ''} disabled={running} onClick={() => setMode('sim')}>{t('ltModeSim')}</button>
            <button className={mode === 'real' ? 'on' : ''} disabled={running} onClick={() => setMode('real')}>{t('ltModeReal')}</button>
          </div>
          <button className="btn primary" disabled={running} onClick={run}>
            {running ? t('ltRunning') : t('ltRun')}
          </button>
          {running && <button className="btn" onClick={stop}>{t('ltStop')}</button>}
          {st && !running && <button className="btn ghost" onClick={teardown}>{t('ltTeardown')}</button>}
        </div>
      </div>

      <div className="lt-steps">
        {STEP_KEYS.map((k, i) => (
          <div key={k} className={`lt-step ${i < step ? 'done' : ''} ${i === step ? 'active' : ''}`}>
            <span className="lt-dot" />{t(k)}
          </div>
        ))}
      </div>

      <div className="lt-body">
        <div className="lt-chart">
          <EChart option={chartOption(st, t)} height={300} />
        </div>
        <div className="lt-aside">
          <div className={`lt-node ${st?.scaled ? 'scaled' : ''}`}>
            <div className="lt-node-top">
              <span className="lt-node-name">{node?.hostname || 'loadtest-sim-01'}</span>
              <span className={`lt-status s-${(node?.status || 'idle').toLowerCase()}`}>{node?.status || '—'}</span>
            </div>
            <div className="lt-node-row"><span>{t('ltMachine')}</span><b>{node?.machine_type || 'e2-small'}</b></div>
            <div className="lt-node-row"><span>{t('ltSpec')}</span>
              <b>{(node?.vcpu ?? 2)} vCPU · {gb(node?.memory_mb ?? 2048)} GB</b>
            </div>
            {st?.scaled && <div className="lt-badge">{t('ltScaledBadge')}</div>}
          </div>
          {st?.cpu_now != null && (
            <div className="lt-cpu-now">
              <span>{t('ltCpu')}</span>
              <b className={st.cpu_now > st.threshold ? 'bad' : 'good'}>{st.cpu_now}%</b>
            </div>
          )}
          <ul className="lt-events">
            {(st?.events || []).map((e) => (
              <li key={e.key}><span className={`ev-dot ev-${e.kind}`} />{t(e.key)}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
