import React from 'react';
import { Card, Empty } from 'antd';

const Settings: React.FC = () => (
  <Card title="⚙️ 系统设置" style={{ background: '#161b22', border: '1px solid #30363d' }}
    styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}>
    <Empty description="设置页面开发中" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  </Card>
);
export default Settings;
