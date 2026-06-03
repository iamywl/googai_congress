// Resizing guidance card: current vs recommended allocation, projected saving,
// and the SLO confidence the recommendation preserves.
export default function RecommendationCard({ recommendation: rec }) {
  const vcpuDelta = rec.current_vcpu - rec.recommended_vcpu;
  const memDelta = rec.current_memory_mb - rec.recommended_memory_mb;
  const downsizing = vcpuDelta > 0 || memDelta > 0;

  return (
    <div className="panel">
      <h3>Resizing Recommendation</h3>
      <div className="rec-grid">
        <div>
          <span className="label">vCPU</span>
          <div className="rec-value">
            <span className="from">{rec.current_vcpu}</span>
            <span className="arrow">→</span>
            <span className="to">{rec.recommended_vcpu}</span>
          </div>
        </div>
        <div>
          <span className="label">Memory</span>
          <div className="rec-value">
            <span className="from">{(rec.current_memory_mb / 1024).toFixed(0)}G</span>
            <span className="arrow">→</span>
            <span className="to">{(rec.recommended_memory_mb / 1024).toFixed(0)}G</span>
          </div>
        </div>
      </div>
      <div className="metric-row">
        <span>Est. cost saving</span>
        <strong className={downsizing ? 'good' : ''}>
          {rec.est_cost_saving_pct.toFixed(0)}%
        </strong>
      </div>
      <div className="metric-row">
        <span>SLO confidence</span>
        <strong>{rec.slo_confidence.toFixed(2)}%</strong>
      </div>
      <p className="rec-note">
        {downsizing
          ? `Headroom detected — downsizing keeps utilisation under target while holding ${rec.slo_confidence}% availability.`
          : 'Current allocation is near-optimal for the forecasted load.'}
      </p>
    </div>
  );
}
