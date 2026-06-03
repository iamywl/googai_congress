// Audit trail of forecasts run and resizes applied — persisted server-side, so
// it survives reloads and makes the "predict → resize" loop tangible.
export default function ActivityLog({ actions }) {
  if (!actions.length) {
    return (
      <div className="panel">
        <h3>Activity Log</h3>
        <p className="rec-note">No actions yet. Apply a resize or run a forecast.</p>
      </div>
    );
  }

  const fmt = (ts) => (ts ? ts.replace('T', ' ').slice(5, 19) : '');

  return (
    <div className="panel">
      <h3>Activity Log</h3>
      <ul className="log">
        {actions.map((a) => (
          <li key={a.id} className={`log-item ${a.action_type.toLowerCase()}`}>
            <span className="log-tag">{a.action_type}</span>
            <div className="log-body">
              <span className="log-detail">{a.detail}</span>
              <span className="log-meta">
                {fmt(a.ts)}
                {a.saving_pct != null && a.saving_pct > 0 && (
                  <em className="log-saving">−{a.saving_pct}% capacity</em>
                )}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
