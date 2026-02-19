import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Layout, Typography, Empty, Spin, Alert, Menu } from 'antd';
import { DashboardOutlined, LineChartOutlined } from '@ant-design/icons';
import CategoryTree from './components/CategoryTree';
import WorkTimePlot from './components/WorkTimePlot';
import BaselineControls from './components/BaselineControls';
import Dashboard from './components/Dashboard';
import {
  fetchCategories,
  fetchRecords,
  fetchResults,
  fetchBaselineConfig,
  saveBaselineConfig,
  deleteBaselineConfig,
} from './services/api';
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

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [collapsed, setCollapsed] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState(null);

  const [categories, setCategories] = useState([]);
  const [records, setRecords] = useState([]);

  const [trend, setTrend] = useState(null);
  const [anomalies, setAnomalies] = useState([]);

  const [baselineStatus, setBaselineStatus] = useState('unconfigured');
  const [baselineRange, setBaselineRange] = useState(null);
  const [excludedIndices, setExcludedIndices] = useState([]);
  const [sensitivity, setSensitivity] = useState(0.5);
  const [savingBaseline, setSavingBaseline] = useState(false);

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

  // カテゴリ選択時にデータを取得
  const loadCategoryData = useCallback(async (categoryId) => {
    setSelectedCategoryId(categoryId);
    if (categoryId == null) {
      setRecords([]);
      setTrend(null);
      setAnomalies([]);
      setBaselineStatus('unconfigured');
      setBaselineRange(null);
      setExcludedIndices([]);
      setSensitivity(0.5);
      return;
    }
    setLoadingRecords(true);
    setError(null);
    try {
      const [recs, results] = await Promise.all([
        fetchRecords(categoryId),
        fetchResults(categoryId),
      ]);
      setRecords(recs);
      setTrend(results.trend);
      setAnomalies(results.anomalies || []);

      try {
        const baselineDef = await fetchBaselineConfig(categoryId);
        setBaselineStatus('configured');
        setBaselineRange({ start: baselineDef.baseline_start, end: baselineDef.baseline_end });
        setSensitivity(baselineDef.sensitivity);
        const excludedDates = new Set(baselineDef.excluded_points.map((d) => d));
        const indices = recs
          .map((r, i) => (excludedDates.has(r.recorded_at) ? i : -1))
          .filter((i) => i >= 0);
        setExcludedIndices(indices);
      } catch (err) {
        if (err.response && err.response.status === 404) {
          setBaselineStatus('unconfigured');
          setBaselineRange(null);
          setExcludedIndices([]);
          setSensitivity(0.5);
        } else {
          throw err;
        }
      }
    } catch (err) {
      setError(`データ取得エラー: ${err.message}`);
    } finally {
      setLoadingRecords(false);
    }
  }, []);

  const handleSaveBaseline = useCallback(async () => {
    if (!selectedCategoryId || !baselineRange) return;
    setSavingBaseline(true);
    try {
      const excludedPoints = excludedIndices.map((i) => records[i].recorded_at);
      await saveBaselineConfig(selectedCategoryId, {
        baseline_start: baselineRange.start,
        baseline_end: baselineRange.end,
        sensitivity,
        excluded_points: excludedPoints,
      });
      setBaselineStatus('configured');
      const results = await fetchResults(selectedCategoryId);
      setTrend(results.trend);
      setAnomalies(results.anomalies || []);
    } catch (err) {
      setError(`設定保存エラー: ${err.message}`);
    } finally {
      setSavingBaseline(false);
    }
  }, [selectedCategoryId, baselineRange, excludedIndices, sensitivity, records]);

  const handleDeleteBaseline = useCallback(async () => {
    if (!selectedCategoryId) return;
    try {
      await deleteBaselineConfig(selectedCategoryId);
      setBaselineStatus('unconfigured');
      setBaselineRange(null);
      setExcludedIndices([]);
      setSensitivity(0.5);
      setAnomalies([]);
      const results = await fetchResults(selectedCategoryId);
      setTrend(results.trend);
      setAnomalies(results.anomalies || []);
    } catch (err) {
      setError(`設定リセットエラー: ${err.message}`);
    }
  }, [selectedCategoryId]);

  const toggleExclude = useCallback((idx) => {
    setExcludedIndices((prev) =>
      prev.includes(idx) ? prev.filter((i) => i !== idx) : [...prev, idx],
    );
  }, []);

  const handleNavigateToPlot = useCallback((categoryId) => {
    setCurrentView('plot');
    loadCategoryData(categoryId);
  }, [loadCategoryData]);

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
                    onSelect={loadCategoryData}
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
            {currentView === 'dashboard' ? (
              <div className="plot-container">
                <Dashboard
                  categories={categories}
                  onNavigateToPlot={handleNavigateToPlot}
                />
              </div>
            ) : (
              <div className="plot-container">
                {selectedCategoryId ? (
                  <>
                    <Title level={4}>作業時間プロット</Title>
                    {loadingRecords ? (
                      <Spin style={STYLE_SPINNER} />
                    ) : records.length > 0 ? (
                      <>
                        <WorkTimePlot
                          records={records}
                          trend={trend}
                          anomalies={anomalies}
                          sensitivity={sensitivity}
                          baselineRange={baselineRange}
                          excludedIndices={excludedIndices}
                          baselineStatus={baselineStatus}
                          onBaselineSelect={setBaselineRange}
                          onToggleExclude={toggleExclude}
                        />
                        <BaselineControls
                          baselineStatus={baselineStatus}
                          baselineRange={baselineRange}
                          sensitivity={sensitivity}
                          onSensitivityChange={setSensitivity}
                          onSave={handleSaveBaseline}
                          onDelete={handleDeleteBaseline}
                          savingBaseline={savingBaseline}
                          hasAnomalies={anomalies.length > 0}
                        />
                      </>
                    ) : (
                      <Empty description="この分類にはレコードがありません" />
                    )}
                  </>
                ) : (
                  <Empty description="左のツリーから分類を選択してください" />
                )}
              </div>
            )}
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;
