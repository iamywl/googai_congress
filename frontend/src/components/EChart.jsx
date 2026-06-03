import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

// A clean, paper/Grafana-style light theme: dark text on transparent panels, a
// light grid, and a restrained categorical palette (colour lives in the series).
const PAPER = {
  color: ['#3274d9', '#1a9850', '#c07d0a', '#d23b3b', '#7c4dff', '#0a9396', '#b5179e'],
  backgroundColor: 'transparent',
  textStyle: { color: '#1b1f24', fontFamily: 'Inter, Segoe UI, system-ui, sans-serif' },
  title: { textStyle: { color: '#11151a', fontWeight: 600 } },
  legend: { textStyle: { color: '#5b636d' } },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#d4d8de' } },
    axisTick: { lineStyle: { color: '#d4d8de' } },
    axisLabel: { color: '#5b636d' },
    splitLine: { show: false, lineStyle: { color: '#eceef1' } },
  },
  valueAxis: {
    axisLine: { show: false },
    axisLabel: { color: '#5b636d' },
    splitLine: { lineStyle: { color: '#eceef1' } },
    nameTextStyle: { color: '#5b636d' },
  },
  tooltip: { textStyle: { color: '#1b1f24' } },
};
echarts.registerTheme('paper', PAPER);

// Thin React wrapper around an ECharts instance. The chart is initialised once
// against a DOM node and updated in place when `option` changes, which keeps a
// large time-series re-render off the React reconciliation path.
export default function EChart({ option, height = 320 }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    chartRef.current = echarts.init(containerRef.current, 'paper');
    const handleResize = () => chartRef.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chartRef.current?.dispose();
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, true);
  }, [option]);

  return <div ref={containerRef} style={{ width: '100%', height }} />;
}
