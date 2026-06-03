import EChart from './EChart.jsx';

// Radial utilisation gauge with green / amber / red zones around the target
// band. Gives an instant read on how loaded a host is.
export default function Gauge({ value, label }) {
  const option = {
    backgroundColor: 'transparent',
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        radius: '92%',
        center: ['50%', '58%'],
        progress: { show: false },
        axisLine: {
          lineStyle: {
            width: 14,
            color: [
              [0.65, '#1a9850'],
              [0.85, '#c07d0a'],
              [1, '#d23b3b'],
            ],
          },
        },
        pointer: { itemStyle: { color: 'auto' }, length: '62%', width: 5 },
        axisTick: { show: false },
        splitLine: { length: 10, lineStyle: { color: 'auto', width: 2 } },
        axisLabel: { color: '#5b636d', fontSize: 10, distance: -28 },
        anchor: { show: true, size: 10, itemStyle: { color: 'auto' } },
        detail: {
          valueAnimation: true,
          formatter: '{value}%',
          color: '#11151a',
          fontSize: 26,
          offsetCenter: [0, '40%'],
        },
        title: { offsetCenter: [0, '74%'], color: '#5b636d', fontSize: 12 },
        data: [{ value: Math.round(value), name: label }],
      },
    ],
  };
  return <EChart option={option} height={200} />;
}
