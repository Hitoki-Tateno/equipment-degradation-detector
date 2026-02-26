import React, { useEffect, useState } from 'react';
import { Typography, Spin, Empty, Segmented, Alert } from 'antd';
import { SelectOutlined, ZoomInOutlined } from '@ant-design/icons';
import WorkTimePlot from './WorkTimePlot';
import BaselineControls from './BaselineControls';
import { useBaselineManager } from '../hooks/useBaselineManager';
import { fetchFeatureRegistry } from '../services/api';

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
 * ズーム/パン状態は Plotly の uirevision に委譲（React 側で管理しない）。
 */
function PlotView({ categoryId }) {
  const {
    records, trend, anomalies,
    baselineStatus, baselineRange, setBaselineRange,
    excludedIndices, sensitivity, setSensitivity,
    featureConfig, setFeatureConfig,
    savingBaseline, interactionMode, setInteractionMode,
    loadingRecords, error, clearError,
    saveBaseline, deleteBaseline, toggleExclude,
  } = useBaselineManager(categoryId);

  const [registry, setRegistry] = useState([]);
  useEffect(() => {
    fetchFeatureRegistry().then(setRegistry).catch(() => {});
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
            categoryId={categoryId}
            onBaselineSelect={setBaselineRange}
            onToggleExclude={toggleExclude}
          />
          <BaselineControls
            baselineStatus={baselineStatus}
            baselineRange={baselineRange}
            sensitivity={sensitivity}
            onSensitivityChange={setSensitivity}
            registry={registry}
            featureConfig={featureConfig}
            onFeatureConfigChange={setFeatureConfig}
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
