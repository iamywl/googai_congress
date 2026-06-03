import { useMemo, useState } from 'react';
import InfoTip from './InfoTip.jsx';
import { glossary } from '../glossary.js';
import { useT } from '../i18n.jsx';
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
  const { t, lang } = useT();
  const GL = glossary(lang);
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
    const mt = machineTypes.find((m) => m.name === picked);
    if (mt) onSelectType?.(mt);
  }

  return (
    <div className="panel inner">
      <h3>
        {t('rcTitle')}
        <InfoTip text={GL.resizeTarget} label={t('rcTitle')} />
      </h3>

      <div className="metric-row">
        <span>
          {t('rcCurrent')}
          <InfoTip text={GL.currentAlloc} label={t('rcCurrent')} />
        </span>
        <strong>
          {current} vCPU · {(currentMemoryMb / 1024).toFixed(0)} GB
        </strong>
      </div>
      {currentType && (
        <div className="metric-row">
          <span>
            {t('rcMachine')}
            <InfoTip text={GL.machineType} label={t('rcMachine')} />
          </span>
          <strong className="mtype-chip">{currentType.name}</strong>
        </div>
      )}
      <div className="metric-row">
        <span>
          {t('rcPeak')}
          <InfoTip text={GL.projectedUtil} label={t('rcPeak')} />
        </span>
        <strong className={zone}>{Math.round(util)}%</strong>
      </div>

      {machineTypes.length > 0 && (
        <div className="mtype-picker">
          <label htmlFor="mtype-select">{t('rcResizeTo')}</label>
          <div className="mtype-row">
            <select
              id="mtype-select"
              value={picked}
              disabled={busy}
              onChange={(e) => setPicked(e.target.value)}
            >
              <option value="">{t('rcSelect')}</option>
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
              {t('rcApply')}
            </button>
          </div>
        </div>
      )}

      <div className="btn-row">
        <button className="btn" onClick={onScaleDown} disabled={busy || current <= 1}>
          {t('rcHalve')}
        </button>
        <button className="btn" onClick={onScaleUp} disabled={busy || current >= 256}>
          {t('rcDouble')}
        </button>
      </div>
      <button
        className="btn primary wide"
        onClick={onApply}
        disabled={busy || !canApply}
      >
        {t('rcApplyRec')}{recommended != null ? ` → ${recommended} vCPU` : ''}
      </button>
      <button className="btn wide" onClick={onForecast} disabled={busy}>
        {busy ? t('rcWorking') : t('rcRun')}
      </button>
    </div>
  );
}
