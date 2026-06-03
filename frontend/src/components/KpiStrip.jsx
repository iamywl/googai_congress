import InfoTip from './InfoTip.jsx';
import { GLOSSARY } from '../glossary.js';

// Fleet-level summary cards — an at-a-glance overview above the per-host detail.
export default function KpiStrip({ fleet }) {
  const hosts = fleet.length;
  const reclaimableVcpu = fleet.reduce(
    (sum, f) => sum + Math.max(0, f.rec.current_vcpu - f.rec.recommended_vcpu),
    0,
  );
  const reclaimableGb = fleet.reduce(
    (sum, f) =>
      sum + Math.max(0, f.rec.current_memory_mb - f.rec.recommended_memory_mb),
    0,
  ) / 1024;
  const avgSaving = hosts
    ? Math.round(fleet.reduce((s, f) => s + f.rec.est_cost_saving_pct, 0) / hosts)
    : 0;

  const cards = [
    { label: 'Hosts monitored', value: hosts, unit: '', info: GLOSSARY.hostsMonitored },
    { label: 'Reclaimable vCPU', value: reclaimableVcpu, unit: 'cores', accent: 'good', info: GLOSSARY.reclaimableVcpu },
    { label: 'Reclaimable memory', value: reclaimableGb.toFixed(0), unit: 'GB', accent: 'good', info: GLOSSARY.reclaimableMemory },
    { label: 'Avg. cost saving', value: avgSaving, unit: '%', accent: 'good', info: GLOSSARY.avgSaving },
    { label: 'SLO maintained', value: '99.9', unit: '%', info: GLOSSARY.sloMaintained },
  ];

  return (
    <section className="kpi-strip">
      {cards.map((c) => (
        <div className="kpi-card" key={c.label}>
          <span className="kpi-label">
            {c.label}
            <InfoTip text={c.info} label={c.label} />
          </span>
          <span className="kpi-value">
            <strong className={c.accent || ''}>{c.value}</strong>
            <em>{c.unit}</em>
          </span>
        </div>
      ))}
    </section>
  );
}
