import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Table, Tag, Button, Space, Modal, Typography, Alert, message } from 'antd';
import { DeleteOutlined, ThunderboltOutlined, LineChartOutlined } from '@ant-design/icons';
import { fetchResults, fetchBaselineConfig, deleteBaselineConfig, triggerAnalysis } from '../services/api';
import { flattenLeafCategories } from '../utils/categoryUtils';

const { Title } = Typography;

const STYLE_ALERT_MB = { marginBottom: 16 };
const STYLE_HEADER_ROW = {
  marginBottom: 16,
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};
const STYLE_TITLE_INLINE = { margin: 0 };

function Dashboard({ categories, onNavigateToPlot }) {
  const [dashboardData, setDashboardData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [error, setError] = useState(null);

  const loadDashboardData = useCallback(async () => {
    if (!categories || categories.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const leaves = flattenLeafCategories(categories);
      const data = await Promise.all(
        leaves.map(async (leaf) => {
          const [results, baselineDef] = await Promise.allSettled([
            fetchResults(leaf.id),
            fetchBaselineConfig(leaf.id),
          ]);
          return {
            key: leaf.id,
            categoryId: leaf.id,
            categoryPath: leaf.path,
            trend: results.status === 'fulfilled' ? results.value.trend : null,
            anomalyCount:
              results.status === 'fulfilled' ? (results.value.anomalies || []).length : 0,
            baselineStatus: baselineDef.status === 'fulfilled' ? 'configured' : 'unconfigured',
          };
        }),
      );
      setDashboardData(data);
    } catch (err) {
      setError(`ダッシュボードデータ取得エラー: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [categories]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const handleRunAnalysis = async () => {
    setAnalysisRunning(true);
    try {
      const result = await triggerAnalysis();
      message.success(`分析完了: ${result.processed_categories} カテゴリ処理しました`);
      await loadDashboardData();
    } catch (err) {
      message.error(`分析実行エラー: ${err.message}`);
    } finally {
      setAnalysisRunning(false);
    }
  };

  const handleDeleteBaseline = useCallback(
    (categoryId) => {
      Modal.confirm({
        title: '設定をリセットしますか？',
        content: '異常検知結果もすべて削除されます。この操作は取り消せません。',
        okText: 'リセット',
        okType: 'danger',
        cancelText: 'キャンセル',
        onOk: async () => {
          await deleteBaselineConfig(categoryId);
          await loadDashboardData();
        },
      });
    },
    [loadDashboardData],
  );

  const columns = useMemo(
    () => [
      {
        title: 'カテゴリ',
        dataIndex: 'categoryPath',
        key: 'categoryPath',
        render: (text, record) => (
          <a onClick={() => onNavigateToPlot(record.categoryId)}>{text}</a>
        ),
      },
      {
        title: 'ベースライン設定',
        dataIndex: 'baselineStatus',
        key: 'baselineStatus',
        render: (status) =>
          status === 'configured' ? (
            <Tag color="green">設定済み</Tag>
          ) : (
            <Tag color="default">未設定</Tag>
          ),
        filters: [
          { text: '設定済み', value: 'configured' },
          { text: '未設定', value: 'unconfigured' },
        ],
        onFilter: (value, record) => record.baselineStatus === value,
      },
      {
        title: 'トレンド警告',
        dataIndex: 'trend',
        key: 'warning',
        render: (trend) => {
          if (!trend) return <Tag>未分析</Tag>;
          return trend.is_warning ? (
            <Tag color="red">警告</Tag>
          ) : (
            <Tag color="green">正常</Tag>
          );
        },
      },
      {
        title: '傾き (slope)',
        dataIndex: 'trend',
        key: 'slope',
        render: (trend) => (trend ? trend.slope.toFixed(4) : '-'),
        sorter: (a, b) => {
          const sa = a.trend ? a.trend.slope : 0;
          const sb = b.trend ? b.trend.slope : 0;
          return sa - sb;
        },
      },
      {
        title: '操作',
        key: 'actions',
        render: (_, record) => (
          <Space>
            <Button
              size="small"
              onClick={() => onNavigateToPlot(record.categoryId)}
              icon={<LineChartOutlined />}
            >
              プロット
            </Button>
            {record.baselineStatus === 'configured' && (
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDeleteBaseline(record.categoryId)}
              >
                設定をリセット
              </Button>
            )}
          </Space>
        ),
      },
    ],
    [onNavigateToPlot, handleDeleteBaseline],
  );

  return (
    <div>
      {error && (
        <Alert
          message={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          style={STYLE_ALERT_MB}
        />
      )}
      <div style={STYLE_HEADER_ROW}>
        <Title level={4} style={STYLE_TITLE_INLINE}>
          監視ダッシュボード
        </Title>
        <Button
          type="primary"
          icon={<ThunderboltOutlined />}
          loading={analysisRunning}
          onClick={handleRunAnalysis}
        >
          分析実行
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={dashboardData}
        loading={loading}
        pagination={false}
        size="middle"
      />
    </div>
  );
}

export default React.memo(Dashboard);
