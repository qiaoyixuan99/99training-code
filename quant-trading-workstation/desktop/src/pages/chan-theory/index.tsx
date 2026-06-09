/**
 * 缠论分析 — 完整分析页面
 * K线图 + 缠论标注 + 全局/局部分析 + 拐点 + 异常点 + 买卖信号
 */
import React, { useState, useCallback, useEffect } from 'react';
import {
  Row, Col, Card, Select, Space, Button, Spin, Empty, Tag,
  Table, Collapse, Descriptions, Statistic, Progress, Badge, Typography,
  Tabs, Alert, Tooltip,
} from 'antd';
import {
  ReloadOutlined, RiseOutlined, FallOutlined, WarningOutlined,
  CheckCircleOutlined, CloseCircleOutlined, AimOutlined,
  ThunderboltOutlined, BugOutlined,
} from '@ant-design/icons';
import KLineChart from '../../components/KLineChart/KLineChart';
import { chanApi, marketApi } from '../../services/api';
import { useStore } from '../../stores/useStore';

const { Text, Title } = Typography;
const { Panel } = Collapse;

interface KLineItem {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface ChanResult {
  symbol: string;
  period: string;
  data_points: number;
  date_range: string[];
  fractals: any[];
  strokes: any[];
  segments: any[];
  centers: any[];
  buy_points: any[];
  sell_points: any[];
  global_analysis: any;
  local_analysis: any;
  turning_points: any[];
  anomalies: any[];
  signals: any[];
}

const PERIOD_OPTIONS = [
  { value: '5m', label: '5分钟' },
  { value: '15m', label: '15分钟' },
  { value: '30m', label: '30分钟' },
  { value: '60m', label: '60分钟' },
  { value: '1d', label: '日线' },
  { value: '1w', label: '周线' },
  { value: '1M', label: '月线' },
];

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

const ChanTheory: React.FC = () => {
  const { activeSymbol, setActiveSymbol } = useStore();
  const [symbol, setSymbol] = useState(activeSymbol || '000001');
  const [period, setPeriod] = useState('1d');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ChanResult | null>(null);
  const [klineData, setKlineData] = useState<KLineItem[]>([]);

  // 同步symbol
  useEffect(() => {
    if (activeSymbol && activeSymbol !== symbol) {
      setSymbol(activeSymbol);
    }
  }, [activeSymbol]);

  const runAnalysis = useCallback(async (sym?: string) => {
    const symToUse = sym || symbol;
    if (!symToUse) return;

    setLoading(true);
    setError(null);

    try {
      // 获取K线数据
      const periodMap: Record<string, string> = {
        '1d': 'daily', '1w': 'weekly', '1M': 'monthly',
      };
      const kPeriod = periodMap[period] || period;
      const kRes = await marketApi.getKline(symToUse, kPeriod, 500);
      setKlineData(kRes.data.data || []);

      // 执行缠论分析
      const res = await chanApi.analyze(symToUse, period);
      setResult(res.data);
      if (!sym) {
        setActiveSymbol(symToUse);
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || '分析失败');
      setKlineData([]);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [symbol, period]);

  useEffect(() => {
    if (symbol) {
      runAnalysis(symbol);
    }
  }, [period]);

  const ga = result?.global_analysis;
  const la = result?.local_analysis;

  // ── 趋势标记 ──
  const trendTag = (trend: string) => {
    const map: Record<string, { color: string; icon: React.ReactNode }> = {
      bullish: { color: 'red', icon: <RiseOutlined /> },
      bearish: { color: 'green', icon: <FallOutlined /> },
      ranging: { color: 'orange', icon: <span>⟷</span> },
      unknown: { color: 'default', icon: '?' },
    };
    const t = map[trend] || map.unknown;
    return <Tag color={t.color} icon={t.icon}>{trend === 'bullish' ? '多头' : trend === 'bearish' ? '空头' : trend === 'ranging' ? '震荡' : trend}</Tag>;
  };

  // ── 风险标记 ──
  const riskTag = (risk: string) => {
    const map: Record<string, { color: string }> = {
      high: { color: 'red' }, medium: { color: 'orange' }, low: { color: 'green' },
    };
    const r = map[risk] || map.medium;
    return <Tag color={r.color}>{risk === 'high' ? '高风险' : risk === 'low' ? '低风险' : '中风险'}</Tag>;
  };

  // ── 拐点表格列 ──
  const tpColumns = [
    {
      title: '日期', dataIndex: 'date', key: 'date', width: 100,
      render: (v: string) => <Text style={{ color: '#8b949e', fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '类型', dataIndex: 'type', key: 'type', width: 60,
      render: (v: string) => (
        <Tag color={v === 'top' ? 'red' : 'green'} style={{ fontSize: 11 }}>
          {v === 'top' ? '顶' : '底'}
        </Tag>
      ),
    },
    {
      title: '价格', dataIndex: 'price', key: 'price', width: 80,
      render: (v: number) => <Text strong style={{ color: '#e6edf3' }}>{v}</Text>,
    },
    {
      title: '级别', dataIndex: 'level', key: 'level', width: 70,
      render: (v: string) => {
        const map: Record<string, string> = { major: '主要', medium: '中等', minor: '次要' };
        const color: Record<string, string> = { major: 'red', medium: 'orange', minor: 'default' };
        return <Tag color={color[v]}>{map[v] || v}</Tag>;
      },
    },
    {
      title: '局部振幅', dataIndex: 'local_range_pct', key: 'local_range_pct', width: 80,
      render: (v: number) => `${v}%`,
    },
    {
      title: '量比', dataIndex: 'volume_ratio', key: 'volume_ratio', width: 60,
      render: (v: number) => {
        if (v > 2) return <Text style={{ color: '#ff6666' }}>{v}x</Text>;
        if (v < 0.5) return <Text style={{ color: '#888' }}>{v}x</Text>;
        return `${v}x`;
      },
    },
    {
      title: '趋势位置', dataIndex: 'trend_position', key: 'trend_position', width: 80,
      render: (v: string) => {
        const map: Record<string, string> = { leading: '领先', reversal: '反转', normal: '正常' };
        return map[v] || v;
      },
    },
    {
      title: '异常', dataIndex: 'anomalies', key: 'anomalies',
      render: (v: string[]) => {
        if (!v || v.length === 0) return <Text style={{ color: '#555' }}>—</Text>;
        return (
          <Space size={2} wrap>
            {v.map((a, i) => (
              <Tooltip key={i} title={a}>
                <WarningOutlined style={{ color: '#faad14' }} />
              </Tooltip>
            ))}
          </Space>
        );
      },
    },
  ];

  // ── 异常点表格列 ──
  const anomColumns = [
    {
      title: '日期', dataIndex: 'date', key: 'date', width: 100,
      render: (v: string) => <Text style={{ color: '#8b949e', fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '类型', dataIndex: 'type', key: 'type', width: 100,
      render: (v: string) => {
        const map: Record<string, { color: string; label: string }> = {
          volume_spike: { color: 'volcano', label: '量能异常' },
          price_gap: { color: 'purple', label: '价格缺口' },
          divergence: { color: 'red', label: '背驰' },
          false_break: { color: 'orange', label: '假突破' },
          abnormal_range: { color: 'magenta', label: '异常振幅' },
        };
        const m = map[v] || { color: 'default', label: v };
        return <Tag color={m.color}>{m.label}</Tag>;
      },
    },
    {
      title: '严重度', dataIndex: 'severity', key: 'severity', width: 70,
      render: (v: string) => (
        <Badge
          status={v === 'high' ? 'error' : v === 'medium' ? 'warning' : 'default'}
          text={v === 'high' ? '高' : v === 'medium' ? '中' : '低'}
        />
      ),
    },
    {
      title: '描述', dataIndex: 'description', key: 'description',
      render: (v: string) => <Text style={{ color: '#c9d1d9', fontSize: 12 }}>{v}</Text>,
    },
  ];

  // ── 信号表格列 ──
  const signalColumns = [
    {
      title: '日期', dataIndex: 'date', key: 'date', width: 100,
      render: (v: string) => <Text style={{ color: '#8b949e', fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '方向', dataIndex: 'direction', key: 'direction', width: 60,
      render: (v: string) => (
        <Tag color={v === 'buy' ? 'red' : 'green'}>
          {v === 'buy' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    {
      title: '类型', dataIndex: 'type', key: 'type', width: 80,
      render: (v: string) => {
        const map: Record<string, string> = {
          buy1: '一买', buy2: '二买', buy3: '三买',
          sell1: '一卖', sell2: '二卖', sell3: '三卖',
          divergence: '背驰',
        };
        return <Text style={{ color: '#e6edf3', fontSize: 12 }}>{map[v] || v}</Text>;
      },
    },
    {
      title: '价格', dataIndex: 'price', key: 'price', width: 80,
      render: (v: number) => <Text style={{ color: '#e6edf3' }}>{v > 0 ? v.toFixed(2) : '—'}</Text>,
    },
    {
      title: '置信度', dataIndex: 'confidence', key: 'confidence', width: 80,
      render: (v: number) => (
        <Progress
          percent={Math.round(v * 100)}
          size="small"
          strokeColor={v > 0.7 ? '#52c41a' : v > 0.5 ? '#faad14' : '#ff4d4f'}
          style={{ width: 60 }}
        />
      ),
    },
    {
      title: '描述', dataIndex: 'description', key: 'description',
      render: (v: string) => <Text style={{ color: '#c9d1d9', fontSize: 11 }}>{v}</Text>,
      ellipsis: true,
    },
  ];

  // ── 分型标记数据映射 ──
  const fractalOverlays = result?.turning_points?.map((tp: any) => ({
    index: tp.index,
    date: tp.date,
    type: tp.type,
    price: tp.price,
    level: tp.level,
  })) || [];

  const strokeOverlays = result?.strokes?.map((s: any) => ({
    start_index: s.start_index,
    end_index: s.end_index,
    start_date: s.start_date,
    end_date: s.end_date,
    direction: s.direction,
    start_price: s.start_price,
    end_price: s.end_price,
  })) || [];

  const centerOverlays = result?.centers?.map((c: any) => ({
    zg: c.zg,
    zd: c.zd,
    start_index: c.start_index,
    end_index: c.end_index,
    start_date: c.start_date,
    end_date: c.end_date,
  })) || [];

  const buyOverlays = result?.buy_points?.map((p: any) => ({
    index: p.index,
    date: p.date,
    type: p.type,
    price: p.price,
  })) || [];

  const sellOverlays = result?.sell_points?.map((p: any) => ({
    index: p.index,
    date: p.date,
    type: p.type,
    price: p.price,
  })) || [];

  // ── 统计 ──
  const majorTP = result?.turning_points?.filter((t: any) => t.level === 'major').length || 0;
  const mediumTP = result?.turning_points?.filter((t: any) => t.level === 'medium').length || 0;
  const highAnomalies = result?.anomalies?.filter((a: any) => a.severity === 'high').length || 0;
  const totalSignals = (result?.buy_points?.length || 0) + (result?.sell_points?.length || 0);

  return (
    <div style={{ padding: '0 0 16px 0' }}>
      {/* ── 顶栏：股票输入 + 周期选择 ── */}
      <Card
        size="small"
        style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
        styles={{ body: { padding: '12px 16px' } }}
      >
        <Row align="middle" gutter={16}>
          <Col>
            <Text strong style={{ color: '#e6edf3' }}>🧠 缠论分析</Text>
          </Col>
          <Col flex="auto">
            <Space size={8}>
              <Select
                showSearch
                value={symbol}
                onChange={(v) => { setSymbol(v); runAnalysis(v); }}
                style={{ width: 160 }}
                placeholder="股票代码"
                options={QUICK_SYMBOLS.map(s => ({ value: s.code, label: `${s.code} ${s.name}` }))}
                optionFilterProp="label"
              />
              <Select
                value={period}
                onChange={setPeriod}
                style={{ width: 90 }}
                options={PERIOD_OPTIONS}
              />
              <Button
                icon={<ReloadOutlined />}
                onClick={() => runAnalysis()}
                loading={loading}
              >
                分析
              </Button>
            </Space>
          </Col>
          {result && (
            <Col>
              <Space size={12}>
                <Text style={{ color: '#8b949e', fontSize: 12 }}>
                  {result.date_range[0]} ~ {result.date_range[1]}
                </Text>
                <Text style={{ color: '#8b949e', fontSize: 12 }}>
                  {result.data_points} 根K线
                </Text>
              </Space>
            </Col>
          )}
        </Row>
      </Card>

      {/* ── 内容区 ── */}
      {loading ? (
        <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Spin size="large" tip="正在执行缠论分析..." />
        </div>
      ) : error ? (
        <Card style={{ background: '#161b22', border: '1px solid #30363d' }}>
          <Alert message="分析错误" description={error} type="error" showIcon />
          <div style={{ marginTop: 16 }}>
            <Text style={{ color: '#8b949e' }}>快捷入口：</Text>
            <Space wrap style={{ marginTop: 8 }}>
              {QUICK_SYMBOLS.map(s => (
                <Button key={s.code} size="small" onClick={() => { setSymbol(s.code); runAnalysis(s.code); }}>
                  {s.code} {s.name}
                </Button>
              ))}
            </Space>
          </div>
        </Card>
      ) : !result ? (
        <Card style={{ background: '#161b22', border: '1px solid #30363d' }}>
          <Empty description="输入股票代码并点击分析" image={Empty.PRESENTED_IMAGE_SIMPLE}>
            <Space wrap>
              {QUICK_SYMBOLS.map(s => (
                <Button key={s.code} size="small" onClick={() => { setSymbol(s.code); runAnalysis(s.code); }}>
                  {s.code} {s.name}
                </Button>
              ))}
            </Space>
          </Empty>
        </Card>
      ) : (
        <Row gutter={12}>
          {/* ── 左侧：K线图 ── */}
          <Col span={16}>
            <Card
              size="small"
              title={
                <Space>
                  <Text style={{ color: '#e6edf3' }}>{result.symbol}</Text>
                  <Tag>{period}</Tag>
                  {trendTag(ga?.trend)}
                </Space>
              }
              style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
              styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
            >
              <KLineChart
                data={klineData}
                height={520}
                showVolume={true}
                period={period}
                fractals={fractalOverlays}
                strokes={strokeOverlays}
                centers={centerOverlays}
                buyPoints={buyOverlays}
                sellPoints={sellOverlays}
              />
              {/* 图例 */}
              <div style={{ marginTop: 8, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                <Space size={4}><span style={{ color: '#44ff44', fontSize: 18 }}>●</span><Text style={{ color: '#8b949e', fontSize: 11 }}>底分型</Text></Space>
                <Space size={4}><span style={{ color: '#ff4444', fontSize: 18 }}>●</span><Text style={{ color: '#8b949e', fontSize: 11 }}>顶分型</Text></Space>
                <Space size={4}><span style={{ color: '#00ff00' }}>▲</span><Text style={{ color: '#8b949e', fontSize: 11 }}>买点</Text></Space>
                <Space size={4}><span style={{ color: '#ff0000' }}>▼</span><Text style={{ color: '#8b949e', fontSize: 11 }}>卖点</Text></Space>
                <Space size={4}><span style={{ borderBottom: '1px dashed gold', width: 20, display: 'inline-block' }} /><Text style={{ color: '#8b949e', fontSize: 11 }}>中枢</Text></Space>
                <Space size={4}><span style={{ borderBottom: '1px dotted #26a69a', width: 20, display: 'inline-block' }} /><Text style={{ color: '#8b949e', fontSize: 11 }}>上升笔</Text></Space>
                <Space size={4}><span style={{ borderBottom: '1px dotted #ef5350', width: 20, display: 'inline-block' }} /><Text style={{ color: '#8b949e', fontSize: 11 }}>下降笔</Text></Space>
              </div>
            </Card>

            {/* ── 全局分析总结 ── */}
            {ga && (
              <Card
                size="small"
                title="📋 全局分析总结"
                style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
                styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
              >
                <Text style={{ color: '#c9d1d9', fontSize: 13, lineHeight: 1.8 }}>
                  {ga.summary}
                </Text>
              </Card>
            )}
          </Col>

          {/* ── 右侧：分析面板 ── */}
          <Col span={8}>
            {/* 全局分析 */}
            {ga && (
              <Card
                size="small"
                title="🌍 全局趋势"
                style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
                styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
              >
                <Row gutter={[8, 8]}>
                  <Col span={12}>
                    <Statistic title="趋势方向" valueRender={() => trendTag(ga.trend)} />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="趋势强度"
                      value={ga.trend_strength}
                      suffix="/100"
                      valueStyle={{ color: ga.trend_strength > 60 ? '#ff6666' : ga.trend_strength < 40 ? '#66ff66' : '#faad14', fontSize: 16 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic title="市场阶段" valueRender={() => {
                      const pm: Record<string, string> = {
                        accumulation: '底部吸筹', uptrend: '上涨趋势',
                        distribution: '顶部派发', downtrend: '下跌趋势', ranging: '区间震荡',
                      };
                      return <Tag>{pm[ga.phase] || ga.phase}</Tag>;
                    }} />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="结构健康度"
                      value={ga.structure_health}
                      suffix="分"
                      valueStyle={{ color: ga.structure_health > 60 ? '#52c41a' : ga.structure_health > 40 ? '#faad14' : '#ff4d4f', fontSize: 16 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic title="关键支撑" value={ga.key_support || '—'} valueStyle={{ color: '#52c41a', fontSize: 14 }} />
                  </Col>
                  <Col span={12}>
                    <Statistic title="关键阻力" value={ga.key_resistance || '—'} valueStyle={{ color: '#ff4d4f', fontSize: 14 }} />
                  </Col>
                  <Col span={24}>
                    {ga.has_segment_divergence && (
                      <Alert message="存在线段级别背驰" type="warning" showIcon style={{ marginTop: 4 }} />
                    )}
                    {ga.center_gravity?.inside_center && (
                      <Alert message="价格处于中枢内部" type="info" showIcon style={{ marginTop: 4 }} />
                    )}
                  </Col>
                </Row>
              </Card>
            )}

            {/* 局部分析 */}
            {la && (
              <Card
                size="small"
                title="📍 当前位置"
                style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
                styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
              >
                <Row gutter={[8, 8]}>
                  <Col span={12}>
                    <Statistic title="当前价格" value={la.current_price} valueStyle={{ color: '#e6edf3', fontSize: 16 }} />
                  </Col>
                  <Col span={12}>
                    <Statistic title="风险等级" valueRender={() => riskTag(la.risk_level)} />
                  </Col>
                  <Col span={12}>
                    <Statistic title="到支撑" value={la.distance_to_support?.toFixed(2) || '—'} valueStyle={{ color: '#52c41a', fontSize: 13 }} />
                  </Col>
                  <Col span={12}>
                    <Statistic title="到阻力" value={la.distance_to_resistance?.toFixed(2) || '—'} valueStyle={{ color: '#ff4d4f', fontSize: 13 }} />
                  </Col>
                  <Col span={24}>
                    <Text style={{ color: '#8b949e', fontSize: 11 }}>
                      当前趋势：<Tag color={la.current_trend === 'up' ? 'red' : 'green'}>{la.current_trend === 'up' ? '上行' : '下行'}</Tag>
                    </Text>
                    {la.pending_signals?.length > 0 && (
                      <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                        {la.pending_signals.map((s: string, i: number) => (
                          <li key={i} style={{ color: '#c9d1d9', fontSize: 11 }}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </Col>
                </Row>
              </Card>
            )}

            {/* 统计概览 */}
            {result && (
              <Card
                size="small"
                title="📊 分析统计"
                style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
                styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
              >
                <Row gutter={[8, 8]}>
                  <Col span={8}>
                    <Statistic title="分型" value={ga?.fractal_count || 0} valueStyle={{ fontSize: 14, color: '#e6edf3' }} />
                    <Text style={{ fontSize: 10, color: '#8b949e' }}>主要: {majorTP} 中等: {mediumTP}</Text>
                  </Col>
                  <Col span={8}>
                    <Statistic title="笔" value={ga?.stroke_count || 0} valueStyle={{ fontSize: 14, color: '#e6edf3' }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="线段" value={ga?.segment_count || 0} valueStyle={{ fontSize: 14, color: '#e6edf3' }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="中枢" value={ga?.center_count || 0} valueStyle={{ fontSize: 14, color: '#e6edf3' }} />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="买卖信号"
                      value={totalSignals}
                      valueStyle={{ fontSize: 14, color: totalSignals > 0 ? '#faad14' : '#8b949e' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="异常点"
                      value={result.anomalies?.length || 0}
                      valueStyle={{ fontSize: 14, color: highAnomalies > 0 ? '#ff4d4f' : '#8b949e' }}
                    />
                  </Col>
                </Row>
              </Card>
            )}

            {/* 多周期共振提示 */}
            {ga?.multi_period_resonance && ga.multi_period_resonance !== 'none' && (
              <Alert
                message={
                  ga.multi_period_resonance === 'resonant_up' ? '⚡ 多周期共振向上 — 强势信号' :
                  ga.multi_period_resonance === 'resonant_down' ? '⚡ 多周期共振向下 — 警惕风险' :
                  '🔄 多周期横盘共振 — 等待方向'
                }
                type={ga.multi_period_resonance === 'resonant_up' ? 'success' :
                  ga.multi_period_resonance === 'resonant_down' ? 'error' : 'info'}
                showIcon
                style={{ marginBottom: 12 }}
              />
            )}
          </Col>
        </Row>
      )}

      {/* ── 底部详情 Tabs ── */}
      {result && (
        <Card
          size="small"
          style={{ marginTop: 12, background: '#161b22', border: '1px solid #30363d' }}
          styles={{ body: { padding: '8px 12px' } }}
        >
          <Tabs
            defaultActiveKey="turning-points"
            items={[
              {
                key: 'turning-points',
                label: <span>🔴 拐点分析 ({result.turning_points?.length || 0})</span>,
                children: (
                  <div>
                    <div style={{ marginBottom: 8 }}>
                      <Space size={8}>
                        <Tag color="red">主要拐点</Tag>
                        <Tag color="orange">中等拐点</Tag>
                        <Tag>次要拐点</Tag>
                        <Text style={{ color: '#8b949e', fontSize: 11 }}>
                          勾选 = 笔端点 | 双击 = 线段端点
                        </Text>
                      </Space>
                    </div>
                    <Table
                      dataSource={result.turning_points || []}
                      columns={tpColumns}
                      rowKey="index"
                      size="small"
                      pagination={{ pageSize: 15, size: 'small' }}
                      scroll={{ y: 400 }}
                      locale={{ emptyText: '暂无拐点' }}
                      rowClassName={(record) => {
                        if (record.level === 'major') return 'chan-major-row';
                        if (record.level === 'medium') return 'chan-medium-row';
                        return '';
                      }}
                    />
                  </div>
                ),
              },
              {
                key: 'anomalies',
                label: <span>⚠️ 异常点 ({result.anomalies?.length || 0})</span>,
                children: (
                  <div>
                    <Space size={8} style={{ marginBottom: 8 }}>
                      <Badge status="error" text={`高严重度: ${highAnomalies}`} />
                      <Badge status="warning" text={`中严重度: ${(result.anomalies?.filter(a => a.severity === 'medium').length || 0)}`} />
                      <Badge status="default" text={`低严重度: ${(result.anomalies?.filter(a => a.severity === 'low').length || 0)}`} />
                    </Space>
                    <Table
                      dataSource={result.anomalies || []}
                      columns={anomColumns}
                      rowKey={(r, i) => `${r.index}-${i}`}
                      size="small"
                      pagination={{ pageSize: 15, size: 'small' }}
                      scroll={{ y: 400 }}
                      locale={{ emptyText: '未发现异常' }}
                    />
                  </div>
                ),
              },
              {
                key: 'signals',
                label: <span>📶 买卖信号 ({totalSignals})</span>,
                children: (
                  <div>
                    <Space size={8} style={{ marginBottom: 8 }}>
                      <Tag color="red">买入 ({result.buy_points?.length || 0})</Tag>
                      <Tag color="green">卖出 ({result.sell_points?.length || 0})</Tag>
                    </Space>
                    {totalSignals === 0 ? (
                      <div style={{ padding: 32, textAlign: 'center' }}>
                        <Empty description="当前分析周期内未发现明确的买卖信号" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                      </div>
                    ) : (
                      <Table
                        dataSource={result.signals || []}
                        columns={signalColumns}
                        rowKey={(r, i) => `${r.index}-${r.type}-${i}`}
                        size="small"
                        pagination={{ pageSize: 15, size: 'small' }}
                        scroll={{ y: 400 }}
                      />
                    )}
                  </div>
                ),
              },
              {
                key: 'components',
                label: '📐 结构树',
                children: (
                  <Collapse
                    ghost
                    items={[
                      {
                        key: 'fractals',
                        label: <Text style={{ color: '#e6edf3' }}>分型列表 ({result.fractals?.length || 0})</Text>,
                        children: (
                          <div style={{ maxHeight: 300, overflow: 'auto' }}>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                              {result.fractals?.map((f, i) => (
                                <Tag key={i} color={f.type === 'top' ? 'red' : 'green'} style={{ fontSize: 10 }}>
                                  {f.date} {f.type === 'top' ? 'T' : 'B'} {f.high || f.low}
                                </Tag>
                              ))}
                            </div>
                          </div>
                        ),
                      },
                      {
                        key: 'strokes',
                        label: <Text style={{ color: '#e6edf3' }}>笔的列表 ({result.strokes?.length || 0})</Text>,
                        children: (
                          <Table
                            dataSource={result.strokes || []}
                            rowKey="start_index"
                            size="small"
                            pagination={{ pageSize: 10, size: 'small' }}
                            columns={[
                              { title: '方向', dataIndex: 'direction', width: 50, render: (v: string) => <Tag color={v === 'up' ? 'red' : 'green'}>{v === 'up' ? '↑' : '↓'}</Tag> },
                              { title: '起点', dataIndex: 'start_date', width: 90, render: (v: string) => <Text style={{ fontSize: 11 }}>{v}</Text> },
                              { title: '终点', dataIndex: 'end_date', width: 90, render: (v: string) => <Text style={{ fontSize: 11 }}>{v}</Text> },
                              { title: '起价', dataIndex: 'start_price', width: 70, render: (v: number) => v.toFixed(2) },
                              { title: '终价', dataIndex: 'end_price', width: 70, render: (v: number) => v.toFixed(2) },
                              { title: '力度%', dataIndex: 'strength', width: 60, render: (v: number) => `${v}%` },
                              { title: 'K线数', dataIndex: 'kline_count', width: 55 },
                            ]}
                          />
                        ),
                      },
                      {
                        key: 'centers',
                        label: <Text style={{ color: '#e6edf3' }}>中枢列表 ({result.centers?.length || 0})</Text>,
                        children: (
                          <Table
                            dataSource={result.centers || []}
                            rowKey="start_index"
                            size="small"
                            pagination={{ pageSize: 10, size: 'small' }}
                            columns={[
                              { title: '上轨ZG', dataIndex: 'zg', width: 70, render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{v}</Text> },
                              { title: '下轨ZD', dataIndex: 'zd', width: 70, render: (v: number) => <Text style={{ color: '#52c41a' }}>{v}</Text> },
                              { title: '中轴', dataIndex: 'zz', width: 70 },
                              { title: '级别', dataIndex: 'level', width: 60 },
                              { title: '起始', dataIndex: 'start_date', width: 90, render: (v: string) => <Text style={{ fontSize: 11 }}>{v}</Text> },
                              { title: '结束', dataIndex: 'end_date', width: 90, render: (v: string) => <Text style={{ fontSize: 11 }}>{v}</Text> },
                              { title: '强度', dataIndex: 'strength', width: 50, render: (v: number) => `${v}` },
                              { title: 'K线数', dataIndex: 'kline_count', width: 55 },
                            ]}
                          />
                        ),
                      },
                    ]}
                  />
                ),
              },
            ]}
          />
        </Card>
      )}

      {/* ── 自定义行样式 ── */}
      <style>{`
        .chan-major-row td { background: rgba(255, 77, 79, 0.08) !important; }
        .chan-medium-row td { background: rgba(250, 173, 20, 0.05) !important; }
        .ant-statistic-title { font-size: 11px !important; }
        .ant-statistic-content { font-size: 14px !important; }
      `}</style>
    </div>
  );
};

export default ChanTheory;
