import EChart from './EChart.jsx';

// Shows recent CPU history continued by the forecast point estimate and its
// 95% confidence band, plus the model's back-tested MAPE against the 15% target.
export default function ForecastPanel({ metrics, forecast }) {
  const recent = metrics.slice(-12);
  const labels = recent.map((m) => m.ts.slice(11, 16));
  labels.push('+60m');

  const history = recent.map((m) => m.cpu_pct);
  const predicted = new Array(history.length).fill(null);
  predicted.push(forecast.predicted_value);
  history.push(null);

  const band = recent.map(() => [null, null]);
  band.push([forecast.lower_bound, forecast.upper_bound]);

  const mapeOk = forecast.mape != null && forecast.mape <= 15;

  const option = {
    backgroundColor: 'transparent',
    title: { text: 'CPU Forecast (+60m)', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 24, top: 48, bottom: 32 },
    xAxis: { type: 'category', data: labels, boundaryGap: false },
    yAxis: { type: 'value', name: '%' },
    series: [
      { name: 'History', type: 'line', smooth: true, data: history },
      {
        name: 'Forecast', type: 'line', data: predicted,
        symbolSize: 10, lineStyle: { type: 'dashed' },
      },
      {
        name: 'CI lower', type: 'line', stack: 'ci', data: band.map((b) => b[0]),
        lineStyle: { opacity: 0 }, showSymbol: false,
      },
    ],
  };

  return (
    <div className="panel">
      <EChart option={option} height={240} />
      <div className="metric-row">
        <span>Predicted</span>
        <strong>{forecast.predicted_value.toFixed(1)}%</strong>
      </div>
      <div className="metric-row">
        <span>95% interval</span>
        <strong>
          {forecast.lower_bound.toFixed(1)} – {forecast.upper_bound.toFixed(1)}%
        </strong>
      </div>
      <div className="metric-row">
        <span>MAPE (target ≤ 15%)</span>
        <strong className={mapeOk ? 'good' : 'warn'}>
          {forecast.mape == null ? 'n/a' : `${forecast.mape.toFixed(1)}%`}
        </strong>
      </div>
    </div>
  );
}
