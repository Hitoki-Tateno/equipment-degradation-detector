import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Table, Tag, Button, Space, Modal, Typography, Alert, message } from 'antd';
import { DeleteOutlined, ThunderboltOutlined, LineChartOutlined } from '@ant-design/icons';
import { fetchDashboardSummary, fetchResults, fetchBaselineConfig, deleteBaselineConfig, triggerAnalysis } from '../services/api';

const { Title } = Typography;

const STYLE_ALERT_MB = { marginBottom: 16 };
const STYLE_HEADER_ROW = {
  marginBottom: 16,
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};
const STYLE_TITLE_INLINE = { margin: 0 };

const SSE_DEBOUNCE_MS = 2000;

function Dashboard({ active, categories, onNavigateToPlot }) {
  const [dashboardData, setDashboardData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [error, setError] = useState(null);

  // SSE 受信時に非アクティブなら stale フラグを立て、復帰時に再取得
  const staleRef = useRef(false);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summaries = await fetchDashboardSummary();
      setDashboardData(
        summaries.map((s) => ({
          key: s.category_id,
          categoryId: s.category_id,
          categoryPath: s.category_path,
          trend: s.trend,
          anomalyCount: s.anomaly_count,
          baselineStatus: s.baseline_status,
        })),
      );
      staleRef.current = false;
    } catch (err) {
      setError(`ダッシュボードデータ取得エラー: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  // 初回ロード + アクティブ復帰時の再取得
  useEffect(() => {
    if (!active) return;
    // 初回（データ未取得）または stale 時に取得
    if (dashboardData.length === 0 || staleRef.current) {
      if (categories && categories.length > 0) loadDashboardData();
    }
  }, [active, categories, loadDashboardData, dashboardData.length]);

  // SSE 接続: バックエンドのデータ変更を監視
  useEffect(() => {
    const es = new EventSource('/api/events');
    let debounceTimer = null;

    const handleUpdate = () => {
      if (active) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => loadDashboardData(), SSE_DEBOUNCE_MS);
      } else {
        staleRef.current = true;
      }
    };

    es.addEventListener('dashboard-updated', handleUpdate);

    return () => {
      clearTimeout(debounceTimer);
      es.removeEventListener('dashboard-updated', handleUpdate);
      es.close();
    };
  }, [active, loadDashboardData]);

  const handleRunAnalysis = async () => {
    setAnalysisRunning(true);
    try {
      const result = await triggerAnalysis();
      message.success(`分析完了: ${result.processed_categories} カテゴリ処理しました`);
      // SSE 経由で dashboard-updated が届くが、分析実行ボタンの
      // ローディング表示と同期するため明示的にも取得する
      await loadDashboardData();
    } catch (err) {
      message.error(`分析実行エラー: ${err.message}`);
    } finally {
      setAnalysisRunning(false);
    }
  };

  // ダッシュボード上の単行削除用（#72 パターン維持）
  const updateSingleRow = useCallback(async (categoryId) => {
    const [results, baselineDef] = await Promise.allSettled([
      fetchResults(categoryId),
      fetchBaselineConfig(categoryId),
    ]);
    setDashboardData((prev) =>
      prev.map((row) =>
        row.categoryId === categoryId
          ? {
              ...row,
              trend: results.status === 'fulfilled' ? results.value.trend : null,
              anomalyCount:
                results.status === 'fulfilled'
                  ? (results.value.anomalies || []).length
                  : 0,
              baselineStatus:
                baselineDef.status === 'fulfilled' ? 'configured' : 'unconfigured',
            }
          : row,
      ),
    );
  }, []);

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
          await updateSingleRow(categoryId);
        },
      });
    },
    [updateSingleRow],
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
