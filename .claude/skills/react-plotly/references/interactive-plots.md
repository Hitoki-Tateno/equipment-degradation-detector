# Plotly.js インタラクション実装

## react-plotly.js の基本

```jsx
import Plot from "react-plotly.js";

<Plot
  data={[{
    x: nValues,
    y: workTimes,
    mode: "markers",
    type: "scatter",
    marker: { color: markerColors, size: 8 },
  }]}
  layout={{
    dragmode: "select",  // Box Select を有効化
    xaxis: { title: "回数 (n)" },
    yaxis: { title: "作業時間 (秒)" },
  }}
  onSelected={handleSelected}
  onClick={handleClick}
/>
```

## ベースライン範囲選択（Box Select）

```jsx
const handleSelected = (event) => {
  if (event && event.range) {
    const { x } = event.range;
    setBaselineRange({ start: x[0], end: x[1] });
  }
};
```

`layout.dragmode = "select"` でBox Selectが有効になる。ユーザーがドラッグすると `onSelected` が発火し、選択範囲を取得できる。

## 除外点のクリック選択

```jsx
const handleClick = (event) => {
  const pointIndex = event.points[0].pointIndex;
  setExcludedIndices(prev =>
    prev.includes(pointIndex)
      ? prev.filter(i => i !== pointIndex)  // トグル: 解除
      : [...prev, pointIndex]               // トグル: 追加
  );
};
```

## 感度スライダー

```jsx
const [sensitivity, setSensitivity] = useState(0.5);

// anomalyScores は GET /api/results から取得済み
const threshold = computeThreshold(sensitivity);
const markerColors = anomalyScores.map(score =>
  score < threshold ? "red" : "blue"
);
```

`computeThreshold` はsensitivity（0〜1）をscore_samplesの閾値に変換する関数。sensitivityが高いほど閾値が緩く（異常判定が増える）なるように設計する。

## 回帰直線の重ね描き

```jsx
data={[
  // 散布図
  { x: nValues, y: workTimes, mode: "markers", type: "scatter" },
  // 回帰直線
  {
    x: [nValues[0], nValues[nValues.length - 1]],
    y: [intercept + slope * nValues[0], intercept + slope * nValues[nValues.length - 1]],
    mode: "lines",
    type: "scatter",
    line: { color: "red", dash: "dash" },
    name: "トレンド",
  },
]}
```
