import EChart from './EChart.jsx';

// Multi-series time-series chart for a host's CPU / memory / network metrics.
export default function MetricChart({ metrics }) {
  const timestamps = metrics.map((m) => m.ts.replace('T', ' ').slice(5, 16));

  const option = {
    backgroundColor: 'transparent',
    title: { text: 'Resource Utilisation (7-day)', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['CPU %', 'Memory %', 'Net In Kbps', 'Net Out Kbps'], top: 28 },
    grid: { left: 48, right: 24, top: 72, bottom: 48 },
    xAxis: { type: 'category', data: timestamps, boundaryGap: false },
    yAxis: [
      { type: 'value', name: '%', max: 100, position: 'left' },
      { type: 'value', name: 'Kbps', position: 'right' },
    ],
    series: [
      {
        name: 'CPU %', type: 'line', smooth: true, showSymbol: false,
        areaStyle: { opacity: 0.15 }, data: metrics.map((m) => m.cpu_pct),
      },
      {
        name: 'Memory %', type: 'line', smooth: true, showSymbol: false,
        data: metrics.map((m) => m.mem_pct),
      },
      {
        name: 'Net In Kbps', type: 'line', smooth: true, showSymbol: false,
        yAxisIndex: 1, data: metrics.map((m) => m.net_in_kbps),
      },
      {
        name: 'Net Out Kbps', type: 'line', smooth: true, showSymbol: false,
        yAxisIndex: 1, data: metrics.map((m) => m.net_out_kbps),
      },
    ],
  };

  return <EChart option={option} />;
}
