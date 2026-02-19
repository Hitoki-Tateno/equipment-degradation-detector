import React, { useMemo, useCallback } from 'react';
import Plot from 'react-plotly.js';

function computeThreshold(sensitivity, anomalies) {
  if (!anomalies || anomalies.length === 0) return 0;
  const scores = anomalies.map((a) => a.anomaly_score);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  return min + sensitivity * (max - min);
}

const PLOT_STYLE = { width: '100%', height: '400px' };

function WorkTimePlot({
  records,
  trend,
  anomalies,
  sensitivity,
  baselineRange,
  excludedIndices,
  modelStatus,
  onBaselineSelect,
  onToggleExclude,
}) {
  const x = useMemo(() => records.map((r) => r.recorded_at), [records]);
  const y = useMemo(() => records.map((r) => r.work_time), [records]);
  const n = x.length;

  const anomalyMap = useMemo(() => {
    const map = {};
    if (anomalies) {
      anomalies.forEach((a) => {
        map[a.recorded_at] = a.anomaly_score;
      });
    }
    return map;
  }, [anomalies]);

  const threshold = useMemo(
    () => computeThreshold(sensitivity, anomalies),
    [sensitivity, anomalies],
  );

  const markerColors = useMemo(() => {
    return records.map((r, i) => {
      if (excludedIndices && excludedIndices.includes(i)) return '#bfbfbf';
      const score = anomalyMap[r.recorded_at];
      if (score !== undefined && score < threshold) return '#ff4d4f';
      return '#1890ff';
    });
  }, [records, excludedIndices, anomalyMap, threshold]);

  const markerSymbols = useMemo(() => {
    return records.map((_, i) =>
      excludedIndices && excludedIndices.includes(i) ? 'x' : 'circle',
    );
  }, [records, excludedIndices]);

  const traces = useMemo(() => {
    const t = [
      {
        x,
        y,
        type: 'scatter',
        mode: 'markers',
        marker: { color: markerColors, size: 8, symbol: markerSymbols },
        name: '作業時間',
      },
    ];
    if (trend && n >= 2) {
      t.push({
        x: [x[0], x[n - 1]],
        y: [
          trend.intercept + trend.slope * 1,
          trend.intercept + trend.slope * n,
        ],
        type: 'scatter',
        mode: 'lines',
        line: { color: 'red', dash: 'dash' },
        name: 'トレンド',
      });
    }
    return t;
  }, [x, y, n, markerColors, markerSymbols, trend]);

  const shapes = useMemo(() => {
    if (!baselineRange) return [];
    return [
      {
        type: 'rect',
        xref: 'x',
        yref: 'paper',
        x0: baselineRange.start,
        x1: baselineRange.end,
        y0: 0,
        y1: 1,
        fillcolor: 'rgba(24, 144, 255, 0.1)',
        line: {
          color: 'rgba(24, 144, 255, 0.5)',
          width: 1,
          dash: 'dot',
        },
      },
    ];
  }, [baselineRange]);

  const handleSelected = useCallback(
    (event) => {
      if (modelStatus === 'defined') return;
      if (event && event.range && event.range.x && onBaselineSelect) {
        onBaselineSelect({
          start: event.range.x[0],
          end: event.range.x[1],
        });
      }
    },
    [modelStatus, onBaselineSelect],
  );

  const handleClick = useCallback(
    (event) => {
      if (modelStatus === 'defined') return;
      if (
        event &&
        event.points &&
        event.points.length > 0 &&
        onToggleExclude
      ) {
        onToggleExclude(event.points[0].pointIndex);
      }
    },
    [modelStatus, onToggleExclude],
  );

  const layout = useMemo(
    () => ({
      dragmode: modelStatus === 'defined' ? 'zoom' : 'select',
      xaxis: { title: '記録日時', type: 'date' },
      yaxis: { title: '作業時間 t (秒)' },
      margin: { t: 20, r: 20 },
      autosize: true,
      shapes,
    }),
    [modelStatus, shapes],
  );

  return (
    <Plot
      data={traces}
      layout={layout}
      onSelected={handleSelected}
      onClick={handleClick}
      useResizeHandler
      style={PLOT_STYLE}
    />
  );
}

export default React.memo(WorkTimePlot);
