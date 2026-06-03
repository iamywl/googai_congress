import InfoTip from './InfoTip.jsx';
import { glossary } from '../glossary.js';
import { useT } from '../i18n.jsx';

// Resizing guidance card: current vs recommended allocation, the nearest GCP
// instance for each, projected saving, and the SLO confidence preserved.
export default function RecommendationCard({ recommendation: rec }) {
  const { t, lang } = useT();
  const GL = glossary(lang);
  const vcpuDelta = rec.current_vcpu - rec.recommended_vcpu;
  const memDelta = rec.current_memory_mb - rec.recommended_memory_mb;
  const downsizing = vcpuDelta > 0 || memDelta > 0;
  const fromType = rec.current_machine_type;
  const toType = rec.recommended_machine_type;

  return (
    <div className="panel">
      <h3>
        {t('recTitle')}
        <InfoTip text={GL.machineType} label={t('recTitle')} />
      </h3>
      <div className="rec-grid">
        <div>
          <span className="label">{t('recVcpu')}</span>
          <div className="rec-value">
            <span className="from">{rec.current_vcpu}</span>
            <span className="arrow">→</span>
            <span className="to">{rec.recommended_vcpu}</span>
          </div>
        </div>
        <div>
          <span className="label">{t('recMemory')}</span>
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
            {t('recInstance')}
            <InfoTip text={GL.machineType} label={t('recInstance')} />
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
          {t('recSaving')}
          <InfoTip text={GL.costSaving} label={t('recSaving')} />
        </span>
        <strong className={downsizing ? 'good' : ''}>
          {rec.est_cost_saving_pct.toFixed(0)}%
        </strong>
      </div>
      <div className="metric-row">
        <span>
          {t('recSlo')}
          <InfoTip text={GL.sloConfidence} label={t('recSlo')} />
        </span>
        <strong>{rec.slo_confidence.toFixed(2)}%</strong>
      </div>
      <p className="rec-note">
        {downsizing ? t('recNoteDown') : t('recNoteOk')}
      </p>
    </div>
  );
}
