import React from 'react';
import { Slider, Button, Space, Modal, Typography, Tag } from 'antd';
import { SaveOutlined, DeleteOutlined } from '@ant-design/icons';

const { Text } = Typography;

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
  const handleDelete = () => {
    Modal.confirm({
      title: 'モデルを削除しますか？',
      content: '異常検知結果もすべて削除されます。この操作は取り消せません。',
      okText: '削除',
      okType: 'danger',
      cancelText: 'キャンセル',
      onOk: onDelete,
    });
  };

  return (
    <div className="model-controls">
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Space>
          <Text strong>モデル状態:</Text>
          {modelStatus === 'defined' ? (
            <Tag color="green">定義済み</Tag>
          ) : (
            <Tag color="default">未定義</Tag>
          )}
        </Space>

        {baselineRange && (
          <Text type="secondary">
            ベースライン期間: {new Date(baselineRange.start).toLocaleDateString()} 〜{' '}
            {new Date(baselineRange.end).toLocaleDateString()}
          </Text>
        )}
        {!baselineRange && modelStatus === 'undefined' && (
          <Text type="secondary">
            プロット上でドラッグしてベースライン期間を選択してください
          </Text>
        )}

        <div>
          <Text>感度: {sensitivity.toFixed(2)}</Text>
          <Slider
            min={0}
            max={1}
            step={0.01}
            value={sensitivity}
            onChange={onSensitivityChange}
            disabled={!hasAnomalies}
            tooltip={{ formatter: (val) => `${(val * 100).toFixed(0)}%` }}
          />
          {!hasAnomalies && (
            <Text type="secondary" style={{ fontSize: 12 }}>
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

export default ModelControls;
