# Plotly.js インタラクション実装

## react-plotly.js の基本構成

WorkTimePlot.jsx が Plotly の描画を担当。全データは `useMemo` でメモ化し、不要な再描画を防止する:

```jsx
import React, { useMemo, useCallback } from 'react';
import Plot from 'react-plotly.js';

const PLOT_STYLE = { width: '100%', height: '400px' };

function WorkTimePlot({
  records, trend, anomalies, sensitivity,
  baselineRange, excludedIndices, interactionMode,
  axisRange, onBaselineSelect, onToggleExclude, onRelayout,
}) {
  const x = useMemo(() => records.map((r) => r.recorded_at), [records]);
  const y = useMemo(() => records.map((r) => r.work_time), [records]);

  const layout = useMemo(() => ({
    dragmode: interactionMode === 'select' ? 'select' : 'zoom',
    xaxis: {
      title: '記録日時', type: 'date',
      ...(axisRange?.x ? { range: axisRange.x, autorange: false } : {}),
    },
    yaxis: {
      title: '作業時間 t (秒)',
      ...(axisRange?.y ? { range: axisRange.y, autorange: false } : {}),
    },
    margin: { t: 20, r: 20 },
    autosize: true,
    shapes,  // ベースライン範囲の矩形
  }), [interactionMode, shapes, axisRange]);

  return (
    <Plot
      data={traces}
      layout={layout}
      onSelected={handleSelected}
      onClick={handleClick}
      onRelayout={onRelayout}
      useResizeHandler
      style={PLOT_STYLE}
    />
  );
}

export default React.memo(WorkTimePlot);
```

## インタラクションモードによる動作分岐

`interactionMode` props で `dragmode` と イベントハンドラの有効/無効を制御:

| `interactionMode` | `dragmode` | ドラッグ操作 | クリック操作 |
|-------------------|-----------|-------------|-------------|
| `'select'` | `'select'` | ベースライン範囲選択 | 除外点トグル |
| `'operate'` | `'zoom'` | ズーム・パン | 無効 |

ハンドラ内で `interactionMode` をガードし、操作モード時はイベントを無視する:

```jsx
const handleSelected = useCallback((event) => {
  if (interactionMode !== 'select') return;  // 操作モードでは無視
  if (event && event.range && event.range.x && onBaselineSelect) {
    onBaselineSelect({ start: event.range.x[0], end: event.range.x[1] });
  }
}, [interactionMode, onBaselineSelect]);

const handleClick = useCallback((event) => {
  if (interactionMode !== 'select') return;  // 操作モードでは無視
  if (event && event.points && event.points.length > 0 && onToggleExclude) {
    onToggleExclude(event.points[0].pointIndex);
  }
}, [interactionMode, onToggleExclude]);
```

## ベースライン範囲の可視化

選択された範囲を半透明の矩形（shape）として表示:

```jsx
const shapes = useMemo(() => {
  if (!baselineRange) return [];
  return [{
    type: 'rect', xref: 'x', yref: 'paper',
    x0: baselineRange.start, x1: baselineRange.end,
    y0: 0, y1: 1,
    fillcolor: 'rgba(24, 144, 255, 0.1)',
    line: { color: 'rgba(24, 144, 255, 0.5)', width: 1, dash: 'dot' },
  }];
}, [baselineRange]);
```

## ズーム状態の維持（Issue #53）

操作モードでズーム/パンした表示範囲を、選択モードに切り替えた際にも維持する。

**状態管理（PlotView.jsx）:**
- `axisRange` state: `{ x: [min, max], y: [min, max] } | null`
- `onRelayout` ハンドラで Plotly の `plotly_relayout` イベントをキャプチャ
- カテゴリ切替時に `axisRange` を `null` にリセット
- autoscale（ホームボタン）操作時にも `null` にリセット

**layout への反映（WorkTimePlot.jsx）:**
- `axisRange` が非 null のとき、`xaxis.range` / `yaxis.range` を明示設定し `autorange: false`
- `axisRange` が null のときはデフォルト動作（autorange）

```jsx
// PlotView.jsx
const [axisRange, setAxisRange] = useState(null);

const handleRelayout = useCallback((update) => {
  if (update['xaxis.range[0]'] && update['xaxis.range[1]']) {
    setAxisRange((prev) => ({
      ...prev,
      x: [update['xaxis.range[0]'], update['xaxis.range[1]']],
    }));
  }
  if (update['yaxis.range[0]'] && update['yaxis.range[1]']) {
    setAxisRange((prev) => ({
      ...prev,
      y: [update['yaxis.range[0]'], update['yaxis.range[1]']],
    }));
  }
  if (update['xaxis.autorange'] || update['yaxis.autorange']) {
    setAxisRange(null);
  }
}, []);
```

## マーカーの色分け（異常スコア × 感度 × 除外状態）

```jsx
// 感度値から閾値を算出（スコアが閾値未満で異常と判定）
function computeThreshold(sensitivity, anomalies) {
  if (!anomalies || anomalies.length === 0) return 0;
  const scores = anomalies.map((a) => a.anomaly_score);
  const min = Math.min(...scores);
  const max = Math.max(...scores);
  return min + sensitivity * (max - min);
}

// 各ポイントの色: 除外=グレー(#bfbfbf), 異常=赤(#ff4d4f), 正常=青(#1890ff)
const markerColors = useMemo(() => {
  return records.map((r, i) => {
    if (excludedIndices && excludedIndices.includes(i)) return '#bfbfbf';
    const score = anomalyMap[r.recorded_at];
    if (score !== undefined && score < threshold) return '#ff4d4f';
    return '#1890ff';
  });
}, [records, excludedIndices, anomalyMap, threshold]);

// 除外ポイントは×マーカー、それ以外は○
const markerSymbols = useMemo(() => {
  return records.map((_, i) =>
    excludedIndices && excludedIndices.includes(i) ? 'x' : 'circle',
  );
}, [records, excludedIndices]);
```

## 回帰直線の重ね描き

```jsx
const traces = useMemo(() => {
  const t = [{
    x, y, type: 'scatter', mode: 'markers',
    marker: { color: markerColors, size: 8, symbol: markerSymbols },
    name: '作業時間',
  }];
  if (trend && n >= 2) {
    t.push({
      x: [x[0], x[n - 1]],
      y: [trend.intercept + trend.slope * 1, trend.intercept + trend.slope * n],
      type: 'scatter', mode: 'lines',
      line: { color: 'red', dash: 'dash' },
      name: 'トレンド',
    });
  }
  return t;
}, [x, y, n, markerColors, markerSymbols, trend]);
```
