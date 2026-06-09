/**
 * 行情看盘 — 主页面
 * 左侧: 自选股列表 + 搜索 | 中间: K线图 | 右侧: 详情面板
 */
import React, { useEffect, useState, useCallback } from 'react';
import { Row, Col, Card, Select, Space, Table, Tag, Spin, Empty, Button } from 'antd';
import { StarOutlined, ReloadOutlined } from '@ant-design/icons';
import KLineChart from '../../components/KLineChart/KLineChart';
import { marketApi } from '../../services/api';
import { useStore } from '../../stores/useStore';

interface KLineItem {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// 常用股票快捷入口
const QUICK_SYMBOLS = [
  { code: '000001', name: '平安银行' },
  { code: '600519', name: '贵州茅台' },
  { code: '000858', name: '五粮液' },
  { code: '300750', name: '宁德时代' },
  { code: '600036', name: '招商银行' },
  { code: '002594', name: '比亚迪' },
  { code: '601318', name: '中国平安' },
  { code: '600276', name: '恒瑞医药' },
];

const Dashboard: React.FC = () => {
  const { activeSymbol, setActiveSymbol, watchlist, addToWatchlist } = useStore();
  const [period, setPeriod] = useState('daily');
  const [klineData, setKlineData] = useState<KLineItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (symbol: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await marketApi.getKline(symbol, period, 300);
      setKlineData(res.data.data || []);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
      setKlineData([]);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    if (activeSymbol) {
      fetchData(activeSymbol);
    }
  }, [activeSymbol, period, fetchData]);

  const latestData = klineData.length > 0 ? klineData[klineData.length - 1] : null;
  const prevData = klineData.length > 1 ? klineData[klineData.length - 2] : null;
  const change = latestData && prevData ? latestData.close - prevData.close : 0;
  const changePct = prevData && prevData.close !== 0 ? (change / prevData.close) * 100 : 0;

  const stockName = QUICK_SYMBOLS.find((s) => s.code === activeSymbol)?.name || '';

  return (
    <div>
      {/* 快捷股票入口 */}
      {!activeSymbol && (
        <Card
          title="📈 股票快捷入口"
          size="small"
          style={{ marginBottom: 16, background: '#161b22', border: '1px solid #30363d' }}
          styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
        >
          <Space wrap size={[8, 8]}>
            {QUICK_SYMBOLS.map((s) => (
              <Button
                key={s.code}
                size="small"
                onClick={() => setActiveSymbol(s.code)}
              >
                {s.code} {s.name}
              </Button>
            ))}
          </Space>
        </Card>
      )}

      {/* K线图区域 */}
      {activeSymbol && (
        <Row gutter={16}>
          <Col span={18}>
            <Card
              size="small"
              style={{ background: '#161b22', border: '1px solid #30363d' }}
              styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
              title={
                <Space>
                  <span>{activeSymbol} {stockName}</span>
                  {latestData && (
                    <>
                      <span style={{ fontSize: 18, fontWeight: 700 }}>
                        {latestData.close.toFixed(2)}
                      </span>
                      <span className={change >= 0 ? 'up' : 'down'}>
                        {change >= 0 ? '+' : ''}{change.toFixed(2)} ({changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%)
                      </span>
                      <Tag color="default">{latestData.date}</Tag>
                    </>
                  )}
                </Space>
              }
              extra={
                <Space>
                  <Select
                    size="small"
                    value={period}
                    onChange={setPeriod}
                    style={{ width: 90 }}
                    options={[
                      { value: '5m', label: '5分钟' },
                      { value: '15m', label: '15分钟' },
                      { value: '30m', label: '30分钟' },
                      { value: '60m', label: '60分钟' },
                      { value: 'daily', label: '日K' },
                      { value: 'weekly', label: '周K' },
                      { value: 'monthly', label: '月K' },
                    ]}
                  />
                  <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchData(activeSymbol)} />
                  <Button
                    size="small"
                    icon={<StarOutlined />}
                    onClick={() => addToWatchlist({ symbol: activeSymbol, name: stockName, group: '默认' })}
                  >
                    加自选
                  </Button>
                </Space>
              }
            >
              {loading ? (
                <div style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Spin size="large" />
                </div>
              ) : error ? (
                <div style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Empty description={`加载失败: ${error}`} />
                </div>
              ) : klineData.length === 0 ? (
                <div style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Empty description="输入股票代码查看K线" />
                </div>
              ) : (
                <KLineChart data={klineData} height={520} symbol="" />
              )}
            </Card>
          </Col>

          {/* 右侧面板 */}
          <Col span={6}>
            <Card
              size="small"
              title="📊 行情数据"
              style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
              styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
            >
              {latestData ? (
                <div style={{ color: '#8b949e', fontSize: 13 }}>
                  <Row justify="space-between" style={{ marginBottom: 6 }}>
                    <span>开盘</span><span style={{ color: '#e6edf3' }}>{latestData.open.toFixed(2)}</span>
                  </Row>
                  <Row justify="space-between" style={{ marginBottom: 6 }}>
                    <span>最高</span><span className="up">{latestData.high.toFixed(2)}</span>
                  </Row>
                  <Row justify="space-between" style={{ marginBottom: 6 }}>
                    <span>最低</span><span className="down">{latestData.low.toFixed(2)}</span>
                  </Row>
                  <Row justify="space-between" style={{ marginBottom: 6 }}>
                    <span>收盘</span><span style={{ color: '#e6edf3', fontWeight: 700 }}>{latestData.close.toFixed(2)}</span>
                  </Row>
                  <Row justify="space-between">
                    <span>成交量</span><span style={{ color: '#e6edf3' }}>{(latestData.volume / 10000).toFixed(0)}万手</span>
                  </Row>
                </div>
              ) : (
                <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>

            {/* 自选股列表 */}
            <Card
              size="small"
              title={`⭐ 自选股 (${watchlist.length})`}
              style={{ background: '#161b22', border: '1px solid #30363d' }}
              styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
            >
              {watchlist.length === 0 ? (
                <div style={{ color: '#8b949e', fontSize: 12, textAlign: 'center', padding: 16 }}>
                  暂无自选股，查看K线时点击"加自选"
                </div>
              ) : (
                <div style={{ maxHeight: 300, overflow: 'auto' }}>
                  {watchlist.map((w) => (
                    <div
                      key={w.symbol}
                      onClick={() => setActiveSymbol(w.symbol)}
                      style={{
                        padding: '6px 8px', cursor: 'pointer', borderRadius: 4,
                        background: activeSymbol === w.symbol ? '#1c3a5c' : 'transparent',
                        color: '#e6edf3', fontSize: 13,
                        marginBottom: 2,
                      }}
                    >
                      {w.symbol} {w.name}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default Dashboard;
