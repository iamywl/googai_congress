// Top navigation menu — switches between the dashboard, the full history
// browser, and the runnable test-scenario view.
const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: '◧' },
  { id: 'history', label: 'History', icon: '🕘' },
  { id: 'tests', label: 'Test Scenarios', icon: '⚙' },
];

export default function NavBar({ view, onChange }) {
  return (
    <nav className="navbar">
      {TABS.map((t) => (
        <button
          key={t.id}
          className={`nav-item ${view === t.id ? 'active' : ''}`}
          onClick={() => onChange(t.id)}
        >
          <span className="nav-icon" aria-hidden="true">{t.icon}</span>
          {t.label}
        </button>
      ))}
    </nav>
  );
}
