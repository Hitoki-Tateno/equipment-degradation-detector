import React, { useState, useEffect, useCallback } from 'react';
import { Layout, Typography, Empty, Spin, Alert } from 'antd';
import { DashboardOutlined } from '@ant-design/icons';
import CategoryTree from './components/CategoryTree';
import WorkTimePlot from './components/WorkTimePlot';
import { fetchCategories, fetchRecords } from './services/api';
import './App.css';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState(null);

  const [categories, setCategories] = useState([]);
  const [records, setRecords] = useState([]);

  const [loadingCategories, setLoadingCategories] = useState(true);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [error, setError] = useState(null);

  // 初回マウント時にカテゴリツリーを取得
  useEffect(() => {
    let cancelled = false;
    setLoadingCategories(true);
    fetchCategories()
      .then((cats) => {
        if (!cancelled) setCategories(cats);
      })
      .catch((err) => {
        if (!cancelled) setError(`カテゴリ取得エラー: ${err.message}`);
      })
      .finally(() => {
        if (!cancelled) setLoadingCategories(false);
      });
    return () => { cancelled = true; };
  }, []);

  // カテゴリ選択時にレコードを取得
  const loadRecords = useCallback((categoryId) => {
    setSelectedCategoryId(categoryId);
    if (categoryId == null) {
      setRecords([]);
      return;
    }
    setLoadingRecords(true);
    setError(null);
    fetchRecords(categoryId)
      .then((recs) => setRecords(recs))
      .catch((err) => setError(`レコード取得エラー: ${err.message}`))
      .finally(() => setLoadingRecords(false));
  }, []);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header className="header">
        <div className="logo">
          <DashboardOutlined style={{ fontSize: '24px', color: '#fff', marginRight: '12px' }} />
          <Title level={3} style={{ color: '#fff', margin: 0, display: 'inline' }}>
            設備劣化検知システム
          </Title>
        </div>
      </Header>
      <Layout>
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          width={280}
          theme="light"
          className="site-sider"
        >
          {!collapsed && (
            <div style={{ padding: '16px' }}>
              <Text type="secondary">分類選択</Text>
              {loadingCategories ? (
                <Spin style={{ display: 'block', marginTop: 24 }} />
              ) : (
                <CategoryTree
                  categories={categories}
                  onSelect={loadRecords}
                />
              )}
            </div>
          )}
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content className="site-content">
            {error && (
              <Alert
                message={error}
                type="error"
                showIcon
                closable
                onClose={() => setError(null)}
                style={{ marginBottom: 16 }}
              />
            )}
            <div className="plot-container">
              {selectedCategoryId ? (
                <>
                  <Title level={4}>作業時間プロット</Title>
                  {loadingRecords ? (
                    <Spin style={{ display: 'block', marginTop: 24 }} />
                  ) : records.length > 0 ? (
                    <WorkTimePlot records={records} />
                  ) : (
                    <Empty description="この分類にはレコードがありません" />
                  )}
                </>
              ) : (
                <Empty description="左のツリーから分類を選択してください" />
              )}
            </div>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;
