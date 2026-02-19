import React, { useState, useCallback, useEffect } from 'react';
import { Typography, Spin, Empty, Segmented, Alert } from 'antd';
import { SelectOutlined, ZoomInOutlined } from '@ant-design/icons';
import WorkTimePlot from './WorkTimePlot';
import BaselineControls from './BaselineControls';
import { useBaselineManager } from '../hooks/useBaselineManager';

const { Title } = Typography;

const STYLE_SPINNER = { display: 'block', marginTop: 24 };
const STYLE_ALERT_MB = { marginBottom: 16 };
const STYLE_SEGMENTED = { marginBottom: 12 };

// インタラクションモード切替トグルの選択肢
// select: ベースライン範囲選択 + 除外点クリック
// operate: ズーム・パン操作
const MODE_OPTIONS = [
  { label: '選択モード', value: 'select', icon: <SelectOutlined /> },
  { label: '操作モード', value: 'operate', icon: <ZoomInOutlined /> },
];

/**
 * プロットビュー: モード切替トグル + 散布図 + ベースライン操作パネル。
 * ベースライン関連のロジックは useBaselineManager hook に委譲。
 */
function PlotView({ categoryId }) {
  const {
    records, trend, anomalies,
    baselineStatus, baselineRange, setBaselineRange,
    excludedIndices, sensitivity, setSensitivity,
    savingBaseline, interactionMode, setInteractionMode,
    loadingRecords, error, clearError,
    saveBaseline, deleteBaseline, toggleExclude,
  } = useBaselineManager(categoryId);

  // ズーム状態を保持（モード切替時にリセットしない）
  const [axisRange, setAxisRange] = useState(null);

  // カテゴリ切替時にズーム状態をリセット
  useEffect(() => {
    setAxisRange(null);
  }, [categoryId]);

  // Plotly の relayout イベントでズーム/パン状態をキャプチャ
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

  if (!categoryId) {
    return <Empty description="左のツリーから分類を選択してください" />;
  }

  return (
    <>
      <Title level={4}>作業時間プロット</Title>
      {error && (
        <Alert
          message={error}
          type="error"
          showIcon
          closable
          onClose={clearError}
          style={STYLE_ALERT_MB}
        />
      )}
      {loadingRecords ? (
        <Spin style={STYLE_SPINNER} />
      ) : records.length > 0 ? (
        <>
          <Segmented
            value={interactionMode}
            onChange={setInteractionMode}
            options={MODE_OPTIONS}
            style={STYLE_SEGMENTED}
          />
          <WorkTimePlot
            records={records}
            trend={trend}
            anomalies={anomalies}
            sensitivity={sensitivity}
            baselineRange={baselineRange}
            excludedIndices={excludedIndices}
            interactionMode={interactionMode}
            axisRange={axisRange}
            onBaselineSelect={setBaselineRange}
            onToggleExclude={toggleExclude}
            onRelayout={handleRelayout}
          />
          <BaselineControls
            baselineStatus={baselineStatus}
            baselineRange={baselineRange}
            sensitivity={sensitivity}
            onSensitivityChange={setSensitivity}
            onSave={saveBaseline}
            onDelete={deleteBaseline}
            savingBaseline={savingBaseline}
            hasAnomalies={anomalies.length > 0}
          />
        </>
      ) : (
        <Empty description="この分類にはレコードがありません" />
      )}
    </>
  );
}

export default React.memo(PlotView);
