import InfoTip from './InfoTip.jsx';
import { GLOSSARY } from '../glossary.js';

// Resizing guidance card: current vs recommended allocation, the nearest GCP
// instance for each, projected saving, and the SLO confidence preserved.
export default function RecommendationCard({ recommendation: rec }) {
  const vcpuDelta = rec.current_vcpu - rec.recommended_vcpu;
  const memDelta = rec.current_memory_mb - rec.recommended_memory_mb;
  const downsizing = vcpuDelta > 0 || memDelta > 0;
  const fromType = rec.current_machine_type;
  const toType = rec.recommended_machine_type;

  return (
    <div className="panel">
      <h3>
        Resizing Recommendation
        <InfoTip text={GLOSSARY.machineType} label="권장안" />
      </h3>
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
      {fromType && toType && (
        <div className="metric-row">
          <span>
            GCP instance
            <InfoTip text={GLOSSARY.machineType} label="머신 타입" />
          </span>
          <strong className="mtype-pair">
            <span className="mtype-chip dim">{fromType.name}</span>
            <span className="arrow">→</span>
            <span className="mtype-chip">{toType.name}</span>
          </strong>
        </div>
      )}
      <div className="metric-row">
        <span>
          Est. cost saving
          <InfoTip text={GLOSSARY.costSaving} label="비용 절감" />
        </span>
        <strong className={downsizing ? 'good' : ''}>
          {rec.est_cost_saving_pct.toFixed(0)}%
        </strong>
      </div>
      <div className="metric-row">
        <span>
          SLO confidence
          <InfoTip text={GLOSSARY.sloConfidence} label="SLO 신뢰도" />
        </span>
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
