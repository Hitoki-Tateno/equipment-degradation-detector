import React, { useState } from 'react';
import { Layout, Typography, Empty } from 'antd';
import { DashboardOutlined } from '@ant-design/icons';
import './App.css';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedCategoryId, setSelectedCategoryId] = useState(null);

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
              {/* CategoryTree: Issue #5 で実装 */}
            </div>
          )}
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content className="site-content">
            <div className="plot-container">
              {selectedCategoryId ? (
                <>
                  <Title level={4}>作業時間プロット</Title>
                  {/* WorkTimePlot: Issue #6 で実装 */}
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
