import React, { useState, useCallback } from 'react';
import { Card, Upload, Button, Alert, Space, Typography, message, Popconfirm } from 'antd';
import { UploadOutlined, DeleteOutlined, InboxOutlined } from '@ant-design/icons';
import { uploadCsv, deleteDebugData, deleteDebugResults, deleteDebugAll } from '../services/api';

const { Title, Text } = Typography;
const { Dragger } = Upload;

const STYLE_CONTAINER = { maxWidth: 640, margin: '0 auto' };
const STYLE_CARD = { marginBottom: 16 };
const STYLE_RESULT_ALERT = { marginTop: 12 };
const STYLE_WARNING_TEXT = { marginBottom: 12, display: 'block' };

/**
 * デバッグ設定ページ。
 * CSVインポートとデータ一括削除をGUIから操作する。
 * props なし・コールバックなしの自己完結型コンポーネント。
 */
function DebugSettings() {
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [deleting, setDeleting] = useState(null);

  const handleUpload = useCallback(async () => {
    if (fileList.length === 0) return;
    setUploading(true);
    setUploadResult(null);
    try {
      const result = await uploadCsv(fileList[0]);
      setUploadResult({ type: 'success', inserted: result.inserted, skipped: result.skipped });
      setFileList([]);
      message.success(`${result.inserted}件追加しました`);
    } catch (err) {
      setUploadResult({ type: 'error', message: err.response?.data?.detail || err.message });
    } finally {
      setUploading(false);
    }
  }, [fileList]);

  const handleDelete = useCallback(async (deleteFn, label, key) => {
    setDeleting(key);
    try {
      await deleteFn();
      message.success(`${label}を削除しました`);
    } catch (err) {
      message.error(`削除エラー: ${err.response?.data?.detail || err.message}`);
    } finally {
      setDeleting(null);
    }
  }, []);

  const handleDeleteData = useCallback(
    () => handleDelete(deleteDebugData, '作業記録', 'data'),
    [handleDelete],
  );
  const handleDeleteResults = useCallback(
    () => handleDelete(deleteDebugResults, '分析結果', 'results'),
    [handleDelete],
  );
  const handleDeleteAll = useCallback(
    () => handleDelete(deleteDebugAll, '全データ', 'all'),
    [handleDelete],
  );

  const draggerProps = {
    accept: '.csv',
    maxCount: 1,
    fileList,
    beforeUpload: (file) => {
      setFileList([file]);
      return false;
    },
    onRemove: () => {
      setFileList([]);
    },
  };

  return (
    <div style={STYLE_CONTAINER}>
      <Title level={4}>デバッグ設定</Title>

      <Card title="CSVインポート" style={STYLE_CARD}>
        <Dragger {...draggerProps}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">CSVファイルをドラッグ&ドロップ</p>
          <p className="ant-upload-hint">またはクリックしてファイルを選択</p>
        </Dragger>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          onClick={handleUpload}
          loading={uploading}
          disabled={fileList.length === 0}
          style={{ marginTop: 12 }}
        >
          アップロード
        </Button>
        {uploadResult && (
          <Alert
            style={STYLE_RESULT_ALERT}
            type={uploadResult.type}
            showIcon
            message={
              uploadResult.type === 'success'
                ? `${uploadResult.inserted}件追加 / ${uploadResult.skipped}件スキップ`
                : uploadResult.message
            }
          />
        )}
      </Card>

      <Card title="データ削除" style={STYLE_CARD}>
        <Text type="warning" style={STYLE_WARNING_TEXT}>
          削除は取り消せません。
        </Text>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Popconfirm
            title="作業記録を全て削除しますか？"
            onConfirm={handleDeleteData}
            okText="削除"
            cancelText="キャンセル"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />} loading={deleting === 'data'}>
              作業記録を削除
            </Button>
          </Popconfirm>
          <Popconfirm
            title="分析結果を全て削除しますか？"
            onConfirm={handleDeleteResults}
            okText="削除"
            cancelText="キャンセル"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />} loading={deleting === 'results'}>
              分析結果を削除
            </Button>
          </Popconfirm>
          <Popconfirm
            title="全データを削除しますか？（作業記録 + 分析結果）"
            onConfirm={handleDeleteAll}
            okText="削除"
            cancelText="キャンセル"
            okButtonProps={{ danger: true }}
          >
            <Button danger type="primary" icon={<DeleteOutlined />} loading={deleting === 'all'}>
              全データを削除
            </Button>
          </Popconfirm>
        </Space>
      </Card>
    </div>
  );
}

export default React.memo(DebugSettings);
