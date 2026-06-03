import InfoTip from './InfoTip.jsx';
import { glossary } from '../glossary.js';
import { useT } from '../i18n.jsx';

// Audit trail of forecasts run and resizes applied — persisted server-side, so
// it survives reloads and makes the "predict → resize" loop tangible.
export default function ActivityLog({ actions }) {
  const { t, lang } = useT();
  const GL = glossary(lang);
  const fmt = (ts) => (ts ? ts.replace('T', ' ').slice(5, 19) : '');

  const head = (
    <h3>
      {t('alTitle')}
      <InfoTip text={GL.activityLog} label={t('alTitle')} />
    </h3>
  );

  if (!actions.length) {
    return (
      <div className="panel">
        {head}
        <p className="rec-note">{t('alEmpty')}</p>
      </div>
    );
  }

  return (
    <div className="panel">
      {head}
      <ul className="log">
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
    </div>
  );
}
