import React, { useCallback, useMemo } from 'react';
import { Slider, Button, Space, Modal, Typography, Tag } from 'antd';
import { SaveOutlined, DeleteOutlined } from '@ant-design/icons';

const { Text } = Typography;

const SENSITIVITY_MARKS = {
  0.25: '低',
  0.5: '中',
  0.75: '高',
};

const STYLE_SPACE_FULL = { width: '100%' };
const STYLE_TOOLTIP_NULL = { formatter: null };
const STYLE_HINT_TEXT = { fontSize: 12 };

function ModelControls({
  modelStatus,
  baselineRange,
  sensitivity,
  onSensitivityChange,
  onSave,
  onDelete,
  savingModel,
  hasAnomalies,
}) {
  const handleDelete = useCallback(() => {
    Modal.confirm({
      title: 'モデルを削除しますか？',
      content: '異常検知結果もすべて削除されます。この操作は取り消せません。',
      okText: '削除',
      okType: 'danger',
      cancelText: 'キャンセル',
      onOk: onDelete,
    });
  }, [onDelete]);

  const baselineDateDisplay = useMemo(() => {
    if (!baselineRange) return null;
    return {
      start: new Date(baselineRange.start).toLocaleDateString(),
      end: new Date(baselineRange.end).toLocaleDateString(),
    };
  }, [baselineRange]);

  return (
    <div className="model-controls">
      <Space direction="vertical" style={STYLE_SPACE_FULL} size="middle">
        <Space>
          <Text strong>モデル状態:</Text>
          {modelStatus === 'defined' ? (
            <Tag color="green">定義済み</Tag>
          ) : (
            <Tag color="default">未定義</Tag>
          )}
        </Space>

        {baselineDateDisplay && (
          <Text type="secondary">
            ベースライン期間: {baselineDateDisplay.start} 〜{' '}
            {baselineDateDisplay.end}
          </Text>
        )}
        {!baselineRange && modelStatus === 'undefined' && (
          <Text type="secondary">
            プロット上でドラッグしてベースライン期間を選択してください
          </Text>
        )}

        <div>
          <Text>感度</Text>
          <Slider
            min={0.25}
            max={0.75}
            step={null}
            marks={SENSITIVITY_MARKS}
            value={sensitivity}
            onChange={onSensitivityChange}
            tooltip={STYLE_TOOLTIP_NULL}
          />
          {!hasAnomalies && (
            <Text type="secondary" style={STYLE_HINT_TEXT}>
              モデルを保存すると異常検知が有効になります
            </Text>
          )}
        </div>

        <Space>
          {modelStatus === 'undefined' ? (
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={onSave}
              loading={savingModel}
              disabled={!baselineRange}
            >
              モデル保存
            </Button>
          ) : (
            <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
              モデル削除
            </Button>
          )}
        </Space>
      </Space>
    </div>
  );
}

export default React.memo(ModelControls);
