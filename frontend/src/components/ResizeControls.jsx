// Interactive HW-sizing controls. Every button issues a REAL, persisted resize
// (or forecast) against the backend, which records an audit-log entry — so the
// "predict → resize → measure" loop is tangible, not a client-side mock.
export default function ResizeControls({
  current,
  recommended,
  util,
  onScaleDown,
  onScaleUp,
  onApply,
  onForecast,
  busy,
}) {
  const zone = util > 85 ? 'warn' : util > 65 ? '' : 'good';
  const canApply = recommended != null && recommended !== current;

  return (
    <div className="panel">
      <h3>Interactive HW Resizing</h3>

      <div className="metric-row">
        <span>Current allocation</span>
        <strong>{current} vCPU</strong>
      </div>
      <div className="metric-row">
        <span>Projected peak utilisation</span>
        <strong className={zone}>{Math.round(util)}%</strong>
      </div>

      <div className="btn-row">
        <button className="btn" onClick={onScaleDown} disabled={busy || current <= 1}>
          ↓ Halve vCPU
        </button>
        <button className="btn" onClick={onScaleUp} disabled={busy || current >= 256}>
          ↑ Double vCPU
        </button>
      </div>
      <button
        className="btn primary wide"
        onClick={onApply}
        disabled={busy || !canApply}
      >
        ✓ Apply AI recommendation{recommended != null ? ` → ${recommended} vCPU` : ''}
      </button>
      <button className="btn wide" onClick={onForecast} disabled={busy}>
        {busy ? 'Working…' : '▶ Run forecast'}
      </button>
    </div>
  );
}
