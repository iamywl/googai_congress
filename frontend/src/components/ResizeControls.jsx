import { useMemo, useState } from 'react';
import InfoTip from './InfoTip.jsx';
import { GLOSSARY } from '../glossary.js';
import { nearestMachineType } from '../api.js';

// Interactive HW-sizing controls. Every button issues a REAL, persisted resize
// (or forecast) against the backend, which records an audit-log entry — so the
// "predict → resize → measure" loop is tangible, not a client-side mock. A GCP
// machine-type dropdown lets an operator snap the host to any predefined
// Google Cloud instance shape.
export default function ResizeControls({
  current,
  currentMemoryMb,
  recommended,
  util,
  onScaleDown,
  onScaleUp,
  onApply,
  onForecast,
  onSelectType,
  machineTypes = [],
  busy,
}) {
  const zone = util > 85 ? 'warn' : util > 65 ? '' : 'good';
  const canApply = recommended != null && recommended !== current;

  // Group the catalogue by series for an <optgroup>-organised dropdown.
  const grouped = useMemo(() => {
    const by = {};
    machineTypes.forEach((m) => {
      (by[m.series] ||= []).push(m);
    });
    return by;
  }, [machineTypes]);

  const currentType = machineTypes.length
    ? nearestMachineType(current, currentMemoryMb, machineTypes)
    : null;
  const [picked, setPicked] = useState('');

  function handleApplyType() {
    const t = machineTypes.find((m) => m.name === picked);
    if (t) onSelectType?.(t);
  }

  return (
    <div className="panel inner">
      <h3>
        Interactive HW Resizing
        <InfoTip text={GLOSSARY.resizeTarget} label="리사이징" />
      </h3>

      <div className="metric-row">
        <span>
          Current allocation
          <InfoTip text={GLOSSARY.currentAlloc} label="현재 할당" />
        </span>
        <strong>
          {current} vCPU · {(currentMemoryMb / 1024).toFixed(0)} GB
        </strong>
      </div>
      {currentType && (
        <div className="metric-row">
          <span>
            GCP machine type
            <InfoTip text={GLOSSARY.machineType} label="머신 타입" />
          </span>
          <strong className="mtype-chip">{currentType.name}</strong>
        </div>
      )}
      <div className="metric-row">
        <span>
          Projected peak utilisation
          <InfoTip text={GLOSSARY.projectedUtil} label="예상 가동률" />
        </span>
        <strong className={zone}>{Math.round(util)}%</strong>
      </div>

      {machineTypes.length > 0 && (
        <div className="mtype-picker">
          <label htmlFor="mtype-select">Resize to GCP instance</label>
          <div className="mtype-row">
            <select
              id="mtype-select"
              value={picked}
              disabled={busy}
              onChange={(e) => setPicked(e.target.value)}
            >
              <option value="">Select machine type…</option>
              {Object.entries(grouped).map(([series, list]) => (
                <optgroup key={series} label={`${series} series`}>
                  {list.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.name} — {m.vcpu} vCPU / {(m.memory_mb / 1024).toFixed(0)} GB
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            <button
              className="btn"
              onClick={handleApplyType}
              disabled={busy || !picked}
            >
              Apply
            </button>
          </div>
        </div>
      )}

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
