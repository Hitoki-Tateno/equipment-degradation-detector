import React from 'react';
import Plot from 'react-plotly.js';

function WorkTimePlot({ records }) {
  const x = records.map((r) => r.recorded_at);
  const y = records.map((r) => r.work_time);

  return (
    <Plot
      data={[
        {
          x,
          y,
          type: 'scatter',
          mode: 'markers',
          marker: { color: '#1890ff', size: 8 },
          name: '作業時間',
        },
      ]}
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
