import EChart from './EChart.jsx';
import InfoTip from './InfoTip.jsx';
import { glossary } from '../glossary.js';
import { useT } from '../i18n.jsx';

// Multi-series time-series chart for a host's CPU / memory / network metrics.
export default function MetricChart({ metrics }) {
  const { t, lang } = useT();
  const GL = glossary(lang);
  const timestamps = metrics.map((m) => m.ts.replace('T', ' ').slice(5, 16));
  const names = [t('mcCpu'), t('mcMem'), t('mcNetIn'), t('mcNetOut')];

  const option = {
    backgroundColor: 'transparent',
    title: { text: t('mcTitle'), textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: names, top: 28 },
    grid: { left: 48, right: 24, top: 72, bottom: 48 },
    xAxis: { type: 'category', data: timestamps, boundaryGap: false },
    yAxis: [
      { type: 'value', name: '%', max: 100, position: 'left' },
      { type: 'value', name: 'Kbps', position: 'right' },
    ],
    series: [
      {
        name: names[0], type: 'line', smooth: true, showSymbol: false,
        areaStyle: { opacity: 0.12 }, data: metrics.map((m) => m.cpu_pct),
      },
      {
        name: names[1], type: 'line', smooth: true, showSymbol: false,
        data: metrics.map((m) => m.mem_pct),
      },
      {
        name: names[2], type: 'line', smooth: true, showSymbol: false,
        yAxisIndex: 1, data: metrics.map((m) => m.net_in_kbps),
      },
      {
        name: names[3], type: 'line', smooth: true, showSymbol: false,
        yAxisIndex: 1, data: metrics.map((m) => m.net_out_kbps),
      },
    ],
  };

  return (
    <div>
      <div className="chart-legend-info">
        <span>CPU<InfoTip text={GL.cpu} label="CPU" /></span>
        <span>Memory<InfoTip text={GL.memory} label="Memory" /></span>
        <span>Net In<InfoTip text={GL.netIn} label="Net In" /></span>
        <span>Net Out<InfoTip text={GL.netOut} label="Net Out" /></span>
      </div>
      <EChart option={option} />
    </div>
  );
}
