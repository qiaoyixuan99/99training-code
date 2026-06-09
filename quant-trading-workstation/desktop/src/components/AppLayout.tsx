/**
 * 应用主布局 — 侧边栏 + 内容区
 */
import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Layout, Menu, Input, Button, Space, Tag
} from 'antd';
import {
  LineChartOutlined, SearchOutlined, ExperimentOutlined,
  CodeOutlined, BranchesOutlined, AimOutlined,
  ThunderboltOutlined, SettingOutlined, PlusOutlined,
  StarOutlined,
} from '@ant-design/icons';
import { useStore } from '../stores/useStore';

const { Sider, Content, Header } = Layout;

const menuItems = [
  { key: '/dashboard', icon: <LineChartOutlined />, label: '行情看盘' },
  { key: '/screener', icon: <SearchOutlined />, label: '智能选股' },
  { key: '/backtest', icon: <ExperimentOutlined />, label: '策略回测' },
  { key: '/strategy-editor', icon: <CodeOutlined />, label: '策略编辑器' },
  { key: '/chan-theory', icon: <BranchesOutlined />, label: '缠论分析' },
  { key: '/market-timing', icon: <AimOutlined />, label: '大盘择时' },
  { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
];

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const { watchlist, activeSymbol, setActiveSymbol } = useStore();

  return (
    <Layout style={{ height: '100vh' }}>
      {/* 侧边栏 */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={220}
        style={{
          background: '#161b22',
          borderRight: '1px solid #30363d',
        }}
        theme="dark"
      >
        <div style={{
          height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center',
          borderBottom: '1px solid #30363d', marginBottom: 8,
        }}>
          <ThunderboltOutlined style={{ color: '#58a6ff', fontSize: 20, marginRight: 8 }} />
          {!collapsed && <span style={{ color: '#e6edf3', fontWeight: 700, fontSize: 14 }}>Quant Workstation</span>}
        </div>

        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          theme="dark"
          style={{ background: 'transparent', borderRight: 0 }}
        />
      </Sider>

      {/* 主内容区 */}
      <Layout>
        <Header style={{
          height: 48, background: '#161b22', borderBottom: '1px solid #30363d',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0 16px',
        }}>
          <Space>
            <Input.Search
              placeholder="输入股票代码, 如 600000"
              size="small"
              style={{ width: 240 }}
              onSearch={(v) => v && setActiveSymbol(v)}
            />
            {activeSymbol && (
              <Tag color="blue" closable onClose={() => setActiveSymbol(null)}>
                {activeSymbol}
              </Tag>
            )}
          </Space>
          <Space>
            <Button size="small" icon={<StarOutlined />}>
              自选股 ({watchlist.length})
            </Button>
          </Space>
        </Header>

        <Content style={{
          background: '#0d1117',
          overflow: 'auto',
          padding: 16,
        }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
