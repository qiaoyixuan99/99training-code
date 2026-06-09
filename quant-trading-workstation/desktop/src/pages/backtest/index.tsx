import React from 'react';
import { Card, Empty } from 'antd';

const Backtest: React.FC = () => (
  <Card title="⚡ 策略回测" style={{ background: '#161b22', border: '1px solid #30363d' }}
    styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}>
    <Empty description="回测模块开发中 (Phase 4)" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  </Card>
);
export default Backtest;
