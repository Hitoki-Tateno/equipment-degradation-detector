import React, { useMemo, useCallback, useRef, useEffect } from 'react';
import Plotly from 'plotly.js-gl2d-dist';
import createPlotlyComponent from 'react-plotly.js/factory';

const Plot = createPlotlyComponent(Plotly);

// 感度値から異常スコアの閾値を算出（スコアが閾値超過で異常と判定。0〜1、1=異常）
// スコアは原論文準拠の 0-1 スケールで正規化済みのため、絶対値で判定する（ADR 決定5）
function computeThreshold(sensitivity) {
  return 1.0 - sensitivity;
}

const PLOT_STYLE_DEFAULT = { width: '100%', height: '400px' };
const PLOT_STYLE_WITH_SUB = { width: '100%', height: '560px' };

/**
 * 作業時間の散布図。Plotly.jsで描画し、ドラッグ選択・クリック操作を処理する。
 *
 * interactionMode により動作が切り替わる:
 * - 'select': ドラッグでベースライン範囲選択、クリックで除外点トグル
 * - 'operate': ズーム・パン操作
 *
 * ズーム/パン状態は Plotly の uirevision に委譲。
 * 選択ハイライトのクリアは命令的 API (Plotly.restyle) で実行。
 */
function WorkTimePlot({
  records,
  trend,
  anomalies,
  sensitivity,
  baselineRange,
  excludedIndices,
  interactionMode,
  categoryId,
  onBaselineSelect,
  onToggleExclude,
}) {
  const x = useMemo(() => records.map((r) => r.recorded_at), [records]);
  const y = useMemo(() => records.map((r) => r.work_time), [records]);
  const n = x.length;

  // Plotly DOM 要素の参照（命令的API用）
  const graphDivRef = useRef(null);

  const handlePlotInitialized = useCallback((_figure, graphDiv) => {
    graphDivRef.current = graphDiv;
  }, []);

  // 操作モードに切り替わった際にPlotlyの選択ハイライトを強制クリア
  useEffect(() => {
    if (interactionMode !== 'select' && graphDivRef.current) {
      Plotly.restyle(graphDivRef.current, { selectedpoints: [null] }, [0]);
    }
  }, [interactionMode]);

  const threshold = useMemo(() => computeThreshold(sensitivity), [sensitivity]);

  const hasAnomalies = anomalies && anomalies.length > 0;

  // 各ポイントの色: 除外=グレー, それ以外=青
  const markerColors = useMemo(() => {
    return records.map((_, i) => {
      if (excludedIndices && excludedIndices.includes(i)) return '#bfbfbf';
      return '#1890ff';
    });
  }, [records, excludedIndices]);

  // 除外ポイントは×マーカー、それ以外は○
  const markerSymbols = useMemo(() => {
    return records.map((_, i) =>
      excludedIndices && excludedIndices.includes(i) ? 'x' : 'circle',
    );
  }, [records, excludedIndices]);

  const traces = useMemo(() => {
    const scatterTrace = {
      x,
      y,
      type: 'scattergl',
      mode: 'markers',
      marker: { color: markerColors, size: 8, symbol: markerSymbols },
      name: '作業時間',
    };
    const t = [scatterTrace];
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
    // 異常スコアサブチャート
    if (hasAnomalies) {
      const scoreColors = anomalies.map((a) =>
        a.anomaly_score > threshold ? '#ff4d4f' : '#1890ff',
      );
      t.push({
        x: anomalies.map((a) => a.recorded_at),
        y: anomalies.map((a) => a.anomaly_score),
        type: 'scattergl',
        mode: 'markers',
        marker: { color: scoreColors, size: 6 },
        yaxis: 'y2',
        name: '異常スコア',
        hovertemplate: 'スコア: %{y:.3f}<extra></extra>',
      });
    }
    return t;
  }, [x, y, n, markerColors, markerSymbols, trend, hasAnomalies, anomalies, threshold]);

  // ベースライン範囲の矩形 + 閾値ライン
  const shapes = useMemo(() => {
    const s = [];
    if (baselineRange) {
      s.push({
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
      });
    }
    // 異常スコアサブチャートの閾値ライン
    if (hasAnomalies) {
      s.push({
        type: 'line',
        xref: 'paper',
        yref: 'y2',
        x0: 0,
        x1: 1,
        y0: threshold,
        y1: threshold,
        line: { color: 'rgba(255, 77, 79, 0.6)', width: 2, dash: 'dash' },
      });
    }
    return s;
  }, [baselineRange, hasAnomalies, threshold]);

  // ドラッグ選択完了 → ベースライン範囲をセット（選択モード時のみ）
  const handleSelected = useCallback(
    (event) => {
      if (interactionMode !== 'select') return;
      if (event && event.range && event.range.x && onBaselineSelect) {
        onBaselineSelect({
          start: event.range.x[0],
          end: event.range.x[1],
        });
      }
    },
    [interactionMode, onBaselineSelect],
  );

  // ポイントクリック → 除外点をトグル（選択モード・メインtraceのみ）
  const handleClick = useCallback(
    (event) => {
      if (interactionMode !== 'select') return;
      if (
        event?.points?.length > 0 &&
        event.points[0].curveNumber === 0 &&
        onToggleExclude
      ) {
        onToggleExclude(event.points[0].pointIndex);
      }
    },
    [interactionMode, onToggleExclude],
  );

  const layout = useMemo(
    () => ({
      dragmode: interactionMode === 'select' ? 'select' : 'zoom',
      selectdirection: interactionMode === 'select' ? 'h' : undefined,
      selections: interactionMode === 'select' ? undefined : [],
      // scattergl は dragmode:'select' 時のみ stash.xpx/ypx を計算する（plot.js:275-305）。
      // dragmode 変更だけでは editType:'modebar' のため plot 関数が再実行されない。
      // datarevision (editType:'calc') を連動させ、Plotly.react 内で同期的に recalc+replot を強制する。
      datarevision: interactionMode,
      uirevision: categoryId,
      xaxis: {
        title: '記録日時',
        type: 'date',
      },
      yaxis: {
        title: '作業時間 t (秒)',
        domain: hasAnomalies ? [0.33, 1.0] : [0, 1],
      },
      ...(hasAnomalies && {
        yaxis2: {
          title: '異常スコア',
          domain: [0.0, 0.23],
          range: [0, 1.05],
          anchor: 'x',
        },
      }),
      margin: { t: 20, r: 20 },
      autosize: true,
      shapes,
    }),
    [interactionMode, shapes, categoryId, hasAnomalies],
  );

  return (
    <Plot
      data={traces}
      layout={layout}
      onSelected={handleSelected}
      onClick={handleClick}
      onInitialized={handlePlotInitialized}
      useResizeHandler
      style={hasAnomalies ? PLOT_STYLE_WITH_SUB : PLOT_STYLE_DEFAULT}
    />
  );
}

export default React.memo(WorkTimePlot);
