import { useT } from '../i18n.jsx';

// Top navigation menu — switches between the dashboard, the full history
// browser, and the runnable test-scenario view.
export default function NavBar({ view, onChange }) {
  const { t } = useT();
  const tabs = [
    { id: 'dashboard', label: t('navDashboard'), icon: '◧' },
    { id: 'history', label: t('navHistory'), icon: '🕘' },
    { id: 'tests', label: t('navTests'), icon: '⚙' },
  ];
  return (
    <nav className="navbar">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`nav-item ${view === tab.id ? 'active' : ''}`}
          onClick={() => onChange(tab.id)}
        >
          <span className="nav-icon" aria-hidden="true">{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
