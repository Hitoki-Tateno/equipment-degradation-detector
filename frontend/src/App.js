import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Layout, Typography, Spin, Alert, Menu } from 'antd';
import { DashboardOutlined, LineChartOutlined } from '@ant-design/icons';
import CategoryTree from './components/CategoryTree';
import PlotView from './components/PlotView';
import Dashboard from './components/Dashboard';
import { fetchCategories } from './services/api';
import './App.css';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

const STYLE_LAYOUT_ROOT = { minHeight: '100vh' };
const STYLE_ICON_HEADER = {
  fontSize: '24px',
  color: '#fff',
  marginRight: '12px',
};
const STYLE_TITLE_HEADER = { color: '#fff', margin: 0, display: 'inline' };
const STYLE_MENU_NAV = { marginLeft: 'auto', background: 'transparent' };
const STYLE_PADDING_16 = { padding: '16px' };
const STYLE_SPINNER = { display: 'block', marginTop: 24 };
const STYLE_CONTENT_PADDING = { padding: '24px' };
const STYLE_ALERT_MB = { marginBottom: 16 };

/**
 * アプリケーションシェル。
 * レイアウト（Header / Sider / Content）とビュー切替を管理する。
 * プロットビューの状態管理は PlotView + useBaselineManager に委譲。
 */
function App() {
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard' | 'plot'
  const [collapsed, setCollapsed] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState(null);
  const [categories, setCategories] = useState([]);
  const [loadingCategories, setLoadingCategories] = useState(true);
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

  // ダッシュボードからプロットビューへ遷移
  const handleNavigateToPlot = useCallback((categoryId) => {
    setCurrentView('plot');
    setSelectedCategoryId(categoryId);
  }, []);

  const menuItems = useMemo(
    () => [
      { key: 'dashboard', icon: <DashboardOutlined />, label: 'ダッシュボード' },
      { key: 'plot', icon: <LineChartOutlined />, label: 'プロット' },
    ],
    [],
  );

  const handleMenuClick = useCallback(({ key }) => setCurrentView(key), []);
  const handleCloseError = useCallback(() => setError(null), []);

  return (
    <Layout style={STYLE_LAYOUT_ROOT}>
      <Header className="header">
        <div className="logo">
          <DashboardOutlined style={STYLE_ICON_HEADER} />
          <Title level={3} style={STYLE_TITLE_HEADER}>
            設備劣化検知システム
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[currentView]}
          onClick={handleMenuClick}
          items={menuItems}
          style={STYLE_MENU_NAV}
        />
      </Header>
      <Layout>
        {currentView === 'plot' && (
          <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={setCollapsed}
            width={280}
            theme="light"
            className="site-sider"
          >
            {!collapsed && (
              <div style={STYLE_PADDING_16}>
                <Text type="secondary">分類選択</Text>
                {loadingCategories ? (
                  <Spin style={STYLE_SPINNER} />
                ) : (
                  <CategoryTree
                    categories={categories}
                    onSelect={setSelectedCategoryId}
                  />
                )}
              </div>
            )}
          </Sider>
        )}
        <Layout style={STYLE_CONTENT_PADDING}>
          <Content className="site-content">
            {error && (
              <Alert
                message={error}
                type="error"
                showIcon
                closable
                onClose={handleCloseError}
                style={STYLE_ALERT_MB}
              />
            )}
            <div className="plot-container">
              {currentView === 'dashboard' ? (
                <Dashboard
                  categories={categories}
                  onNavigateToPlot={handleNavigateToPlot}
                />
              ) : (
                <PlotView categoryId={selectedCategoryId} />
              )}
            </div>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;
