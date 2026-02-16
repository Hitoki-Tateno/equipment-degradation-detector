import React from 'react';
import Plot from 'react-plotly.js';

/** @type {{ slope: number, intercept: number }} */
const MOCK_TREND = { slope: 0.05, intercept: 10.0 };

function WorkTimePlot({ records, trend }) {
  const x = records.map((r) => r.recorded_at);
  const y = records.map((r) => r.work_time);

  const { slope, intercept } = trend || MOCK_TREND;
  const n = x.length;

  const traces = [
    {
      x,
      y,
      type: 'scatter',
      mode: 'markers',
      marker: { color: '#1890ff', size: 8 },
      name: '作業時間',
    },
  ];

  if (n >= 2) {
    traces.push({
      x: [x[0], x[n - 1]],
      y: [intercept + slope * 1, intercept + slope * n],
      type: 'scatter',
      mode: 'lines',
      line: { color: 'red', dash: 'dash' },
      name: 'トレンド',
    });
  }

  return (
    <Plot
      data={traces}
      layout={{
        xaxis: { title: '記録日時', type: 'date' },
        yaxis: { title: '作業時間 t (秒)' },
        margin: { t: 20, r: 20 },
        autosize: true,
      }}
      useResizeHandler
      style={{ width: '100%', height: '400px' }}
    />
  );
}

export default WorkTimePlot;
