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

function BaselineControls({
  baselineStatus,
  baselineRange,
  sensitivity,
  onSensitivityChange,
  onSave,
  onDelete,
  savingBaseline,
  hasAnomalies,
}) {
  const handleDelete = useCallback(() => {
    Modal.confirm({
      title: '設定をリセットしますか？',
      content: '異常検知結果もすべて削除されます。この操作は取り消せません。',
      okText: 'リセット',
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
    <div className="baseline-controls">
      <Space direction="vertical" style={STYLE_SPACE_FULL} size="middle">
        <Space>
          <Text strong>ベースライン設定:</Text>
          {baselineStatus === 'configured' ? (
            <Tag color="green">設定済み</Tag>
          ) : (
            <Tag color="default">未設定</Tag>
          )}
        </Space>

        {baselineDateDisplay && (
          <Text type="secondary">
            ベースライン期間: {baselineDateDisplay.start} 〜{' '}
            {baselineDateDisplay.end}
          </Text>
        )}
        {!baselineRange && baselineStatus === 'unconfigured' && (
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
              設定を保存すると異常検知が有効になります
            </Text>
          )}
        </div>

        <Space>
          {baselineStatus === 'unconfigured' ? (
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={onSave}
              loading={savingBaseline}
              disabled={!baselineRange}
            >
              設定を保存
            </Button>
          ) : (
            <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
              設定をリセット
            </Button>
          )}
        </Space>
      </Space>
    </div>
  );
}

export default React.memo(BaselineControls);
