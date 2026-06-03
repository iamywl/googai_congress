import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

// Thin React wrapper around an ECharts instance. The chart is initialised once
// against a DOM node and updated in place when `option` changes, which keeps a
// large time-series re-render off the React reconciliation path.
export default function EChart({ option, height = 320 }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    chartRef.current = echarts.init(containerRef.current, 'dark');
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
