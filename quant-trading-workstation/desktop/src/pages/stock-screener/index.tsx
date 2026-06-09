import React from 'react';
import { Card, Empty } from 'antd';
import { SearchOutlined } from '@ant-design/icons';

const StockScreener: React.FC = () => (
  <Card title="🔍 智能选股" style={{ background: '#161b22', border: '1px solid #30363d' }}
    styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}>
    <Empty description="选股模块开发中 (Phase 3)" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  </Card>
);
export default StockScreener;
