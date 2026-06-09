import React from 'react';
import { Card, Empty } from 'antd';

const StrategyEditor: React.FC = () => (
  <Card title="✏️ 策略编辑器" style={{ background: '#161b22', border: '1px solid #30363d' }}
    styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}>
    <Empty description="策略编辑器开发中 (Phase 5)" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  </Card>
);
export default StrategyEditor;
