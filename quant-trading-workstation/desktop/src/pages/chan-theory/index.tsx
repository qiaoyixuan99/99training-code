/**
 * 缠论分析 — 多时段分析页面
 * 分时 / 日K / 月K / 年K — 独立分析 + 多周期联立概览
 *
 * 缠论底层逻辑：
 *   原始K线 → K线包含处理 → 顶底分型(Fractal) → 笔(Stroke)
 *   → 线段(Segment) → 中枢(Center, ZG/ZD/ZZ)
 *   → MACD背驰判断 → 一二三类买卖点(BuySellPoint)
 *
 * 多时段分析意义：
 *   分时(5m~60m)：精细日内结构，寻找精确买卖点
 *   日K(1d/1w)：中期趋势结构，最常用的核心分析级别
 *   月K(1M)：大级别趋势，判断牛熊格局
 *   年K(1Y)：超长周期，判断历史大底大顶
 *   多周期联立：缠论精髓 — 大级别定方向，小级别找买点
 */
import React, { useState, useCallback, useEffect } from 'react';
import {
  Row, Col, Card, Select, Space, Button, Empty, Tag,
  Table, Statistic, Progress, Badge, Typography,
  Tabs, Alert, Tooltip, Divider, Skeleton, Collapse,
} from 'antd';
import {
  RiseOutlined, FallOutlined, WarningOutlined,
  ClockCircleOutlined, CalendarOutlined, HistoryOutlined, GlobalOutlined,
  ThunderboltOutlined, SyncOutlined, ExpandOutlined,
} from '@ant-design/icons';
import KLineChart from '../../components/KLineChart/KLineChart';
import { chanApi, marketApi } from '../../services/api';
import { useStore } from '../../stores/useStore';

const { Text } = Typography;

// ── 类型定义 ──────────────────────────────

interface KLineItem {
  date: string; open: number; high: number; low: number; close: number; volume: number;
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

// ── 时段分组定义 ─────────────────────────

interface PeriodGroup {
  key: string;
  label: string;
  icon: React.ReactNode;
  subPeriods: { value: string; label: string; desc: string }[];
  /** 缠论对该时段的解读 */
  theoryInterpretation: string;
  /** 该时段的特点 */
  characteristics: string[];
}

const PERIOD_GROUPS: PeriodGroup[] = [
  {
    key: 'intraday',
    label: '分时分析',
    icon: <ClockCircleOutlined />,
    subPeriods: [
      { value: '5m', label: '5分钟', desc: '超短线波段，日内精确买卖点' },
      { value: '15m', label: '15分钟', desc: '日内趋势，短线出入场' },
      { value: '30m', label: '30分钟', desc: '日内+跨日波段结构' },
      { value: '60m', label: '60分钟', desc: '短线趋势，1-3日级别' },
    ],
    theoryInterpretation:
      '分时级别反映最小级别的走势结构，用于"小级别找买点"。' +
      '在大级别(日/月)确定方向后，通过分时K线精确定位入场时机。' +
      '分时中枢突破是短线交易的核心信号。',
    characteristics: [
      '数据量大（200-500根K线），结构精细',
      '适合短线/超短线交易决策',
      '中枢、笔的构建更密集，信号更多',
      '需结合日K方向过滤假信号',
    ],
  },
  {
    key: 'daily',
    label: '日K分析',
    icon: <CalendarOutlined />,
    subPeriods: [
      { value: '1d', label: '日线', desc: '中期趋势，核心分析级别' },
      { value: '1w', label: '周线', desc: '中长趋势，波段方向' },
    ],
    theoryInterpretation:
      '日K是缠论分析的"本级别"（核心分析周期）。' +
      '日线中枢是判断中期趋势最重要的依据，日线笔的完成意味着中期方向转变。' +
      '一二三类买卖点通常在日线上最为可靠。',
    characteristics: [
      '分析最全面，买卖点信号最可靠',
      '日线中枢是中期趋势的核心依据',
      '线段背驰在日线级别最有效',
      '是连接大小级别的桥梁',
    ],
  },
  {
    key: 'monthly',
    label: '月K分析',
    icon: <HistoryOutlined />,
    subPeriods: [
      { value: '1M', label: '月线', desc: '大级别趋势，牛熊判断' },
    ],
    theoryInterpretation:
      '月K反映大级别结构，用于"大级别定方向"。' +
      '月线中枢一旦形成，其支撑/阻力延续数年。月线底背驰往往对应历史大底。' +
      '在月线上升笔中，日线回调都是买入机会。',
    characteristics: [
      '数据量少（60-120根K线），每根K线含义重',
      '中枢持续时间长，级别大',
      '买卖点很少但质量极高',
      '大级别背驰是长线配置信号',
    ],
  },
  {
    key: 'yearly',
    label: '年K分析',
    icon: <GlobalOutlined />,
    subPeriods: [
      { value: '1Y', label: '年线', desc: '超长周期，历史格局' },
    ],
    theoryInterpretation:
      '年K分析反映最宏观的走势格局，用于"看大势"。' +
      '年K的顶底分型识别历史性的牛熊转换点。年K中枢往往横跨数年，' +
      '代表了整个市场对该公司价值的长期共识区间。',
    characteristics: [
      '数据量极少（20-30根K线），需降低笔的构建标准',
      '每根年K线代表一整年的博弈结果',
      '年K中枢是"价值区间"的体现',
      '适合判断是否处于历史大底/大顶',
    ],
  },
];

// ── 快捷股票 ─────────────────────────────

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

const DEFAULT_PERIODS = ['5m', '30m', '1d', '1w', '1M', '1Y'];

// ── 工具函数 ─────────────────────────────

/** 将API返回的results按period索引化 */
function indexResults(results: any[], symbol: string): Map<string, ChanResult> {
  const map = new Map<string, ChanResult>();
  results.forEach((r: any) => {
    if (r.status === 'ok') {
      map.set(r.period, {
        symbol: symbol,
        period: r.period,
        data_points: r.data_points,
        date_range: r.date_range,
        fractals: r.fractals,
        strokes: r.strokes,
        segments: r.segments,
        centers: r.centers,
        buy_points: r.buy_points,
        sell_points: r.sell_points,
        global_analysis: r.global_analysis,
        local_analysis: r.local_analysis,
        turning_points: r.turning_points,
        anomalies: r.anomalies,
        signals: r.signals,
      });
    }
  });
  return map;
}

// ── 主组件 ────────────────────────────────

const ChanTheory: React.FC = () => {
  const { activeSymbol, setActiveSymbol } = useStore();
  const [symbol, setSymbol] = useState(activeSymbol || '000001');
  const [activeGroup, setActiveGroup] = useState<string>('daily');
  const [activePeriod, setActivePeriod] = useState<string>('1d');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 多时段分析缓存：Map<period, ChanResult>
  const [resultCache, setResultCache] = useState<Map<string, ChanResult>>(new Map());
  // K线数据缓存：Map<period, KLineItem[]>
  const [klineCache, setKlineCache] = useState<Map<string, KLineItem[]>>(new Map());
  // 当前各时段加载状态
  const [loadingPeriods, setLoadingPeriods] = useState<Set<string>>(new Set());
  // 是否已做全时段批量分析
  const [batchDone, setBatchDone] = useState(false);

  // 同步 activeSymbol
  useEffect(() => {
    if (activeSymbol && activeSymbol !== symbol) {
      setSymbol(activeSymbol);
    }
  }, [activeSymbol]);

  // 切换分组时自动选第一个子周期
  useEffect(() => {
    const group = PERIOD_GROUPS.find(g => g.key === activeGroup);
    if (group && group.subPeriods.length > 0) {
      const p = group.subPeriods[0].value;
      setActivePeriod(p);
    }
  }, [activeGroup]);

  // ── 批量分析所有时段 ──
  const runFullBatchAnalysis = useCallback(async (sym: string) => {
    if (!sym) return;
    setLoading(true);
    setError(null);
    setBatchDone(false);

    const loadingSet = new Set(DEFAULT_PERIODS);
    setLoadingPeriods(new Set(loadingSet));

    try {
      // 并行获取所有时段的K线数据
      const periodMap: Record<string, string> = {
        '1d': 'daily', '1w': 'weekly', '1M': 'monthly', '1Y': 'yearly',
      };

      const klinePromises = DEFAULT_PERIODS.map(async (p) => {
        const kPeriod = periodMap[p] || p;
        try {
          const res = await marketApi.getKline(sym, kPeriod, 500);
          return { period: p, data: res.data.data || [] };
        } catch {
          return { period: p, data: [] };
        }
      });
      const klineResults = await Promise.all(klinePromises);
      setKlineCache(prev => {
        const next = new Map(prev);
        klineResults.forEach(({ period, data }) => {
          next.set(period, data);
          loadingSet.delete(period);
        });
        return next;
      });

      // 批量缠论分析
      const res = await chanApi.batchAnalyze(sym, DEFAULT_PERIODS);
      const { results } = res.data;

      const indexed = indexResults(results, sym);
      setResultCache(indexed);
      setBatchDone(true);
      setActiveSymbol(sym);

      // 检查是否有全部错误
      const allFailed = results.every((r: any) => r.status !== 'ok');
      if (allFailed) {
        const msgs = results.map((r: any) => `${r.period}: ${r.error}`).join('; ');
        setError(`所有时段分析失败: ${msgs}`);
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || '批量分析失败');
    } finally {
      setLoading(false);
      setLoadingPeriods(new Set());
    }
  }, []);

  // ── 单时段分析（后备） ──
  const runSingleAnalysis = useCallback(async (sym: string, period: string) => {
    if (!sym) return;
    setLoading(true);
    setError(null);

    const loadingSet = new Set([period]);
    setLoadingPeriods(loadingSet);

    try {
      // 获取K线
      const periodMap: Record<string, string> = {
        '1d': 'daily', '1w': 'weekly', '1M': 'monthly', '1Y': 'yearly',
      };
      const kPeriod = periodMap[period] || period;
      const kRes = await marketApi.getKline(sym, kPeriod, 500);
      setKlineCache(prev => {
        const next = new Map(prev);
        next.set(period, kRes.data.data || []);
        return next;
      });

      // 缠论分析
      const res = await chanApi.analyze(sym, period);
      setResultCache(prev => {
        const next = new Map(prev);
        next.set(period, res.data);
        return next;
      });
      setActiveSymbol(sym);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || '分析失败');
    } finally {
      setLoading(false);
      setLoadingPeriods(new Set());
    }
  }, []);

  // ── 加载/切换 ──
  const handleAnalyze = useCallback(() => {
    if (!symbol) return;
    runFullBatchAnalysis(symbol);
  }, [symbol, runFullBatchAnalysis]);

  // 初始加载
  useEffect(() => {
    if (symbol) {
      runFullBatchAnalysis(symbol);
    }
  }, []);

  // ── 当前选中结果 ──
  const currentResult = resultCache.get(activePeriod) || null;
  const currentKline = klineCache.get(activePeriod) || [];
  const currentGroup = PERIOD_GROUPS.find(g => g.key === activeGroup);

  const ga = currentResult?.global_analysis;
  const la = currentResult?.local_analysis;

  // ── 多周期联立汇总 ──
  const getMultiPeriodSummary = () => {
    const summary: { period: string; trend: string; phase: string; health: number; support: number; resist: number; buySignals: number; sellSignals: number }[] = [];
    DEFAULT_PERIODS.forEach(p => {
      const r = resultCache.get(p);
      if (r) {
        summary.push({
          period: p,
          trend: r.global_analysis?.trend || 'unknown',
          phase: r.global_analysis?.phase || '—',
          health: r.global_analysis?.structure_health || 0,
          support: r.global_analysis?.key_support || 0,
          resist: r.global_analysis?.key_resistance || 0,
          buySignals: r.buy_points?.length || 0,
          sellSignals: r.sell_points?.length || 0,
        });
      }
    });
    return summary;
  };

  // ── 趋势标记 ──
  const trendTag = (trend: string, size: 'small' | 'default' = 'default') => {
    const map: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
      bullish: { color: 'red', icon: <RiseOutlined />, text: '多头' },
      bearish: { color: 'green', icon: <FallOutlined />, text: '空头' },
      ranging: { color: 'orange', icon: <span>⟷</span>, text: '震荡' },
      unknown: { color: 'default', icon: '?', text: '未知' },
    };
    const t = map[trend] || map.unknown;
    return <Tag color={t.color} icon={t.icon}>{t.text}</Tag>;
  };

  const riskTag = (risk: string) => {
    const map: Record<string, { color: string; text: string }> = {
      high: { color: 'red', text: '高风险' },
      medium: { color: 'orange', text: '中风险' },
      low: { color: 'green', text: '低风险' },
    };
    const r = map[risk] || map.medium;
    return <Tag color={r.color}>{r.text}</Tag>;
  };

  // ── K线图叠加数据 ──
  const fractalOverlays = currentResult?.turning_points?.map((tp: any) => ({
    index: tp.index, date: tp.date, type: tp.type, price: tp.price, level: tp.level,
  })) || [];

  const strokeOverlays = currentResult?.strokes?.map((s: any) => ({
    start_index: s.start_index, end_index: s.end_index,
    start_date: s.start_date, end_date: s.end_date,
    direction: s.direction, start_price: s.start_price, end_price: s.end_price,
  })) || [];

  const centerOverlays = currentResult?.centers?.map((c: any) => ({
    zg: c.zg, zd: c.zd,
    start_index: c.start_index, end_index: c.end_index,
    start_date: c.start_date, end_date: c.end_date,
  })) || [];

  const buyOverlays = currentResult?.buy_points?.map((p: any) => ({
    index: p.index, date: p.date, type: p.type, price: p.price,
  })) || [];

  const sellOverlays = currentResult?.sell_points?.map((p: any) => ({
    index: p.index, date: p.date, type: p.type, price: p.price,
  })) || [];

  // ── 统计 ──
  const majorTP = currentResult?.turning_points?.filter((t: any) => t.level === 'major').length || 0;
  const totalSignals = (currentResult?.buy_points?.length || 0) + (currentResult?.sell_points?.length || 0);
  const highAnomalies = currentResult?.anomalies?.filter((a: any) => a.severity === 'high').length || 0;

  // ── 表格列定义 ──
  const tpColumns = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 100, render: (v: string) => <Text style={{ color: '#8b949e', fontSize: 12 }}>{v}</Text> },
    { title: '类型', dataIndex: 'type', key: 'type', width: 50, render: (v: string) => <Tag color={v === 'top' ? 'red' : 'green'}>{v === 'top' ? '顶' : '底'}</Tag> },
    { title: '价格', dataIndex: 'price', key: 'price', width: 80, render: (v: number) => <Text strong style={{ color: '#e6edf3' }}>{v}</Text> },
    { title: '级别', dataIndex: 'level', key: 'level', width: 60, render: (v: string) => {
      const m: Record<string, { color: string; label: string }> = { major: { color: 'red', label: '主要' }, medium: { color: 'orange', label: '中等' }, minor: { color: 'default', label: '次要' } };
      return <Tag color={m[v]?.color}>{m[v]?.label || v}</Tag>;
    }},
    { title: '振幅', dataIndex: 'local_range_pct', key: 'amp', width: 60, render: (v: number) => `${v}%` },
    { title: '量比', dataIndex: 'volume_ratio', key: 'vol', width: 55, render: (v: number) => <Text style={{ color: v > 2 ? '#ff6666' : v < 0.5 ? '#888' : undefined }}>{v}x</Text> },
    { title: '趋势', dataIndex: 'trend_position', key: 'trend', width: 60, render: (v: string) => ({ leading: '领先', reversal: '反转', normal: '正常' } as Record<string, string>)[v] || v },
    { title: '异常', dataIndex: 'anomalies', key: 'anom', render: (v: string[]) => v?.length > 0 ? <Space size={2}>{v.map((a, i) => <Tooltip key={i} title={a}><WarningOutlined style={{ color: '#faad14' }} /></Tooltip>)}</Space> : <Text style={{ color: '#555' }}>—</Text> },
  ];

  const signalColumns = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 100, render: (v: string) => <Text style={{ color: '#8b949e', fontSize: 12 }}>{v}</Text> },
    { title: '方向', dataIndex: 'direction', key: 'dir', width: 55, render: (v: string) => <Tag color={v === 'buy' ? 'red' : 'green'}>{v === 'buy' ? '买入' : '卖出'}</Tag> },
    { title: '类型', dataIndex: 'type', key: 'type', width: 65, render: (v: string) => {
      const m: Record<string, string> = { buy1: '一买', buy2: '二买', buy3: '三买', sell1: '一卖', sell2: '二卖', sell3: '三卖', divergence: '背驰' };
      return <Text style={{ color: '#e6edf3', fontSize: 12 }}>{m[v] || v}</Text>;
    }},
    { title: '价格', dataIndex: 'price', key: 'price', width: 80, render: (v: number) => <Text style={{ color: '#e6edf3' }}>{v > 0 ? v.toFixed(2) : '—'}</Text> },
    { title: '置信度', dataIndex: 'confidence', key: 'conf', width: 80, render: (v: number) => <Progress percent={Math.round(v * 100)} size="small" strokeColor={v > 0.7 ? '#52c41a' : v > 0.5 ? '#faad14' : '#ff4d4f'} style={{ width: 60 }} /> },
    { title: '描述', dataIndex: 'description', key: 'desc', render: (v: string) => <Text style={{ color: '#c9d1d9', fontSize: 11 }}>{v}</Text>, ellipsis: true },
  ];

  // ── 渲染：加载骨架 ──
  const renderSkeleton = () => (
    <div style={{ padding: 24 }}>
      <Skeleton active paragraph={{ rows: 3 }} />
      <div style={{ height: 520, background: '#0d1117', borderRadius: 8, marginTop: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <Space direction="vertical" align="center">
            <SyncOutlined spin style={{ fontSize: 32, color: '#8b949e' }} />
            <Text style={{ color: '#8b949e' }}>
              正在加载数据并执行缠论分析...
              {loadingPeriods.size > 0 && (
                <span> ({loadingPeriods.size} 个时段剩余)</span>
              )}
            </Text>
          </Space>
        </div>
      </div>
    </div>
  );

  // ── 渲染：错误状态 ──
  const renderError = () => (
    <Card style={{ background: '#161b22', border: '1px solid #30363d' }}>
      <Alert message="分析错误" description={error} type="error" showIcon />
      <div style={{ marginTop: 16 }}>
        <Space>
          <Button type="primary" onClick={() => runFullBatchAnalysis(symbol)}>重试</Button>
          <Text style={{ color: '#8b949e' }}>或选择快捷入口：</Text>
        </Space>
        <Space wrap style={{ marginTop: 8 }}>
          {QUICK_SYMBOLS.map(s => (
            <Button key={s.code} size="small" onClick={() => { setSymbol(s.code); runFullBatchAnalysis(s.code); }}>
              {s.code} {s.name}
            </Button>
          ))}
        </Space>
      </div>
    </Card>
  );

  // ── 渲染：空状态 ──
  const renderEmpty = () => (
    <Card style={{ background: '#161b22', border: '1px solid #30363d' }}>
      <Empty description="输入股票代码开始缠论多时段分析" image={Empty.PRESENTED_IMAGE_SIMPLE}>
        <Space wrap>
          {QUICK_SYMBOLS.map(s => (
            <Button key={s.code} size="small" onClick={() => { setSymbol(s.code); runFullBatchAnalysis(s.code); }}>
              {s.code} {s.name}
            </Button>
          ))}
        </Space>
      </Empty>
    </Card>
  );

  // ── 渲染：多周期联立概览表格 ──
  const renderMultiPeriodOverview = () => {
    const summary = getMultiPeriodSummary();
    if (summary.length === 0) {
      return <Empty description="尚未完成多周期分析" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
    }

    return (
      <Card
        size="small"
        style={{ background: '#161b22', border: '1px solid #30363d' }}
        styles={{ body: { padding: '12px 16px' } }}
      >
        <Table
          dataSource={summary}
          rowKey="period"
          size="small"
          pagination={false}
          columns={[
            {
              title: '周期', dataIndex: 'period', key: 'period', width: 80,
              render: (v: string) => <Tag style={{ fontWeight: 600 }}>{v}</Tag>,
            },
            {
              title: '趋势', dataIndex: 'trend', key: 'trend', width: 80,
              render: (v: string) => trendTag(v, 'small'),
            },
            {
              title: '阶段', dataIndex: 'phase', key: 'phase', width: 80,
              render: (v: string) => {
                const pm: Record<string, string> = { accumulation: '吸筹', uptrend: '上涨', distribution: '派发', downtrend: '下跌', ranging: '震荡' };
                return <Text style={{ fontSize: 12 }}>{pm[v] || v}</Text>;
              },
            },
            {
              title: '结构健康', dataIndex: 'health', key: 'health', width: 90,
              render: (v: number) => (
                <Progress percent={Math.round(v)} size="small" strokeColor={v > 60 ? '#52c41a' : v > 40 ? '#faad14' : '#ff4d4f'} style={{ width: 70 }} />
              ),
            },
            {
              title: '支撑', dataIndex: 'support', key: 'support', width: 70,
              render: (v: number) => <Text style={{ color: '#52c41a', fontSize: 12 }}>{v > 0 ? v.toFixed(2) : '—'}</Text>,
            },
            {
              title: '阻力', dataIndex: 'resist', key: 'resist', width: 70,
              render: (v: number) => <Text style={{ color: '#ff4d4f', fontSize: 12 }}>{v > 0 ? v.toFixed(2) : '—'}</Text>,
            },
            {
              title: '买点', dataIndex: 'buySignals', key: 'buys', width: 50,
              render: (v: number) => <Badge count={v} showZero overflowCount={99} color="red" size="small" />,
            },
            {
              title: '卖点', dataIndex: 'sellSignals', key: 'sells', width: 50,
              render: (v: number) => <Badge count={v} showZero overflowCount={99} color="green" size="small" />,
            },
          ]}
        />

        {/* 多周期共振分析 */}
        <Divider style={{ margin: '12px 0', borderColor: '#30363d' }} />
        {(() => {
          const trends = summary.filter(s => s.trend !== 'unknown');
          const bullishCount = trends.filter(s => s.trend === 'bullish').length;
          const bearishCount = trends.filter(s => s.trend === 'bearish').length;
          const rangingCount = trends.filter(s => s.trend === 'ranging').length;

          let resonanceMsg = '';
          let resonanceType: 'success' | 'error' | 'warning' | 'info' = 'info';

          if (bullishCount >= 4) {
            resonanceMsg = '🟢 多周期共振向上 — 强势多头格局，大中小级别均看涨';
            resonanceType = 'success';
          } else if (bearishCount >= 4) {
            resonanceMsg = '🔴 多周期共振向下 — 强势空头格局，大中小级别均看跌';
            resonanceType = 'error';
          } else if (rangingCount >= 3) {
            resonanceMsg = '🟡 多周期横盘共振 — 方向不明确，等待突破信号';
            resonanceType = 'warning';
          } else if (bullishCount >= 2 && bearishCount >= 2) {
            resonanceMsg = '⚡ 多周期背离 — 大小级别方向冲突，可能处于转折区域';
            resonanceType = 'warning';
          } else {
            resonanceMsg = '📊 周期间缺乏一致信号，建议聚焦日线级别';
          }

          return <Alert message={resonanceMsg} type={resonanceType} showIcon />;
        })()}
      </Card>
    );
  };

  // ── 主渲染 ────────────────────────────
  return (
    <div style={{ padding: '0 0 16px 0' }}>
      {/* ── 顶栏：股票输入 + 批量分析按钮 ── */}
      <Card
        size="small"
        style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
        styles={{ body: { padding: '12px 16px' } }}
      >
        <Row align="middle" gutter={16} wrap>
          <Col>
            <Text strong style={{ color: '#e6edf3', fontSize: 15 }}>🧠 缠论分析</Text>
            <Text style={{ color: '#8b949e', fontSize: 11, marginLeft: 8 }}>
              分型 → 笔 → 线段 → 中枢 → 买卖点
            </Text>
          </Col>
          <Col flex="auto">
            <Space size={8}>
              <Select
                showSearch
                value={symbol}
                onChange={(v) => { setSymbol(v); runFullBatchAnalysis(v); }}
                style={{ width: 160 }}
                placeholder="股票代码"
                options={QUICK_SYMBOLS.map(s => ({ value: s.code, label: `${s.code} ${s.name}` }))}
                optionFilterProp="label"
              />
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleAnalyze}
                loading={loading}
              >
                全时段批量分析
              </Button>
            </Space>
          </Col>
          {batchDone && (
            <Col>
              <Space size={16}>
                <Badge status="success" text={`${resultCache.size}/${DEFAULT_PERIODS.length} 时段已完成`} />
              </Space>
            </Col>
          )}
        </Row>
      </Card>

      {/* ── 时段选择 Tabs ── */}
      <Card
        size="small"
        style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
        styles={{ body: { padding: '8px 16px' } }}
      >
        <Tabs
          activeKey={activeGroup}
          onChange={(key) => setActiveGroup(key)}
          items={[
            ...PERIOD_GROUPS.map(group => ({
              key: group.key,
              label: (
                <Space size={4}>
                  {group.icon}
                  <span>{group.label}</span>
                </Space>
              ),
              children: (
                <div>
                  {/* 子周期选择 */}
                  <div style={{ marginBottom: 12 }}>
                    <Space size={4} wrap>
                      <Text style={{ color: '#8b949e', fontSize: 12, marginRight: 8 }}>选择周期：</Text>
                      {group.subPeriods.map(sp => (
                        <Tooltip key={sp.value} title={sp.desc}>
                          <Button
                            size="small"
                            type={activePeriod === sp.value ? 'primary' : 'default'}
                            onClick={() => setActivePeriod(sp.value)}
                            loading={loadingPeriods.has(sp.value)}
                            style={{ padding: '0 12px' }}
                          >
                            {sp.label}
                          </Button>
                        </Tooltip>
                      ))}
                    </Space>
                  </div>

                  {/* 缠论解读 */}
                  <Alert
                    message={
                      <div>
                        <Text strong style={{ fontSize: 13 }}>📖 缠论视角解读 — {group.label}</Text>
                        <br />
                        <Text style={{ fontSize: 12, color: '#c9d1d9', lineHeight: 1.6 }}>
                          {group.theoryInterpretation}
                        </Text>
                      </div>
                    }
                    type="info"
                    style={{ marginBottom: 8 }}
                  />
                  <Space size={4} wrap style={{ marginBottom: 4 }}>
                    {group.characteristics.map((c, i) => (
                      <Tag key={i} color="processing" style={{ fontSize: 11 }}>{c}</Tag>
                    ))}
                  </Space>
                </div>
              ),
            })),
            // 多周期联立 Tab
            {
              key: 'overview',
              label: (
                <Space size={4}>
                  <ExpandOutlined />
                  <span>多周期联立</span>
                </Space>
              ),
              children: (
                <div>
                  <Alert
                    message={
                      <div>
                        <Text strong>🔗 多周期联立 — 缠论的核心方法论</Text>
                        <br />
                        <Text style={{ fontSize: 12, color: '#c9d1d9' }}>
                          缠论强调至少三个相邻级别的联立分析：大级别定方向，中级别找结构，小级别找买点。
                          当多个周期同时发出同向信号时（共振），是最可靠的交易机会；
                          当大小周期信号相反时（背离），往往是趋势转折的前兆。
                        </Text>
                      </div>
                    }
                    type="warning"
                    style={{ marginBottom: 12 }}
                  />
                  {renderMultiPeriodOverview()}
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* ── 主内容区 ── */}
      {loading && resultCache.size === 0 ? (
        renderSkeleton()
      ) : error && resultCache.size === 0 ? (
        renderError()
      ) : !currentResult && resultCache.size === 0 ? (
        renderEmpty()
      ) : (
        <>
          {activeGroup !== 'overview' && currentResult && (
            <>
              <Row gutter={12}>
                {/* ── 左侧：K线图 ── */}
                <Col span={16}>
                  <Card
                    size="small"
                    title={
                      <Space>
                        <Text style={{ color: '#e6edf3' }}>{currentResult.symbol}</Text>
                        <Tag color="blue">{activePeriod}</Tag>
                        {ga && trendTag(ga.trend)}
                        {la && riskTag(la.risk_level)}
                        <Text style={{ color: '#8b949e', fontSize: 11 }}>
                          {currentResult.date_range[0]} ~ {currentResult.date_range[1]} · {currentResult.data_points}根K线
                        </Text>
                      </Space>
                    }
                    style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
                    styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
                  >
                    {currentKline.length > 0 ? (
                      <KLineChart
                        data={currentKline}
                        height={540}
                        showVolume={true}
                        period={activePeriod}
                        fractals={fractalOverlays}
                        strokes={strokeOverlays}
                        centers={centerOverlays}
                        buyPoints={buyOverlays}
                        sellPoints={sellOverlays}
                      />
                    ) : (
                      <div style={{ height: 540, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0d1117' }}>
                        <Text style={{ color: '#8b949e' }}>暂无K线数据</Text>
                      </div>
                    )}
                    {/* 图例 */}
                    <div style={{ marginTop: 8, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                      <Space size={4}><span style={{ color: '#44ff44', fontSize: 18 }}>●</span><Text style={{ color: '#8b949e', fontSize: 11 }}>底分型</Text></Space>
                      <Space size={4}><span style={{ color: '#ff4444', fontSize: 18 }}>●</span><Text style={{ color: '#8b949e', fontSize: 11 }}>顶分型</Text></Space>
                      <Space size={4}><span style={{ color: '#00ff00' }}>▲</span><Text style={{ color: '#8b949e', fontSize: 11 }}>买点</Text></Space>
                      <Space size={4}><span style={{ color: '#ff0000' }}>▼</span><Text style={{ color: '#8b949e', fontSize: 11 }}>卖点</Text></Space>
                      <Space size={4}><span style={{ borderBottom: '1px dashed gold', width: 20, display: 'inline-block' }}></span><Text style={{ color: '#8b949e', fontSize: 11 }}>中枢</Text></Space>
                      <Space size={4}><span style={{ borderBottom: '1px dotted #26a69a', width: 20, display: 'inline-block' }}></span><Text style={{ color: '#8b949e', fontSize: 11 }}>上升笔</Text></Space>
                      <Space size={4}><span style={{ borderBottom: '1px dotted #ef5350', width: 20, display: 'inline-block' }}></span><Text style={{ color: '#8b949e', fontSize: 11 }}>下降笔</Text></Space>
                    </div>
                  </Card>

                  {/* 全局分析总结 */}
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
                        <Col span={12}><Statistic title="趋势方向" valueRender={() => trendTag(ga.trend)} /></Col>
                        <Col span={12}>
                          <Statistic title="趋势强度" value={ga.trend_strength} suffix="/100"
                            valueStyle={{ color: ga.trend_strength > 60 ? '#ff6666' : ga.trend_strength < 40 ? '#66ff66' : '#faad14', fontSize: 16 }} />
                        </Col>
                        <Col span={12}>
                          <Statistic title="市场阶段" valueRender={() => {
                            const pm: Record<string, string> = { accumulation: '底部吸筹', uptrend: '上涨趋势', distribution: '顶部派发', downtrend: '下跌趋势', ranging: '区间震荡' };
                            return <Tag>{pm[ga.phase] || ga.phase}</Tag>;
                          }} />
                        </Col>
                        <Col span={12}>
                          <Statistic title="结构健康" value={ga.structure_health} suffix="分"
                            valueStyle={{ color: ga.structure_health > 60 ? '#52c41a' : ga.structure_health > 40 ? '#faad14' : '#ff4d4f', fontSize: 16 }} />
                        </Col>
                        <Col span={12}><Statistic title="关键支撑" value={ga.key_support || '—'} valueStyle={{ color: '#52c41a', fontSize: 14 }} /></Col>
                        <Col span={12}><Statistic title="关键阻力" value={ga.key_resistance || '—'} valueStyle={{ color: '#ff4d4f', fontSize: 14 }} /></Col>
                        <Col span={24}>
                          {ga.has_segment_divergence && <Alert message="存在线段级别背驰" type="warning" showIcon style={{ marginTop: 4 }} />}
                          {ga.center_gravity?.inside_center && <Alert message="价格处于中枢内部" type="info" showIcon style={{ marginTop: 4 }} />}
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
                        <Col span={12}><Statistic title="当前价格" value={la.current_price} valueStyle={{ color: '#e6edf3', fontSize: 16 }} /></Col>
                        <Col span={12}><Statistic title="风险等级" valueRender={() => riskTag(la.risk_level)} /></Col>
                        <Col span={12}><Statistic title="到支撑" value={la.distance_to_support?.toFixed(2) || '—'} valueStyle={{ color: '#52c41a', fontSize: 13 }} /></Col>
                        <Col span={12}><Statistic title="到阻力" value={la.distance_to_resistance?.toFixed(2) || '—'} valueStyle={{ color: '#ff4d4f', fontSize: 13 }} /></Col>
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
                  {currentResult && (
                    <Card
                      size="small"
                      title="📊 分析统计"
                      style={{ marginBottom: 12, background: '#161b22', border: '1px solid #30363d' }}
                      styles={{ header: { color: '#e6edf3', borderBottom: '1px solid #30363d' } }}
                    >
                      <Row gutter={[8, 8]}>
                        <Col span={8}><Statistic title="分型" value={ga?.fractal_count || 0} valueStyle={{ fontSize: 14, color: '#e6edf3' }} /><Text style={{ fontSize: 10, color: '#8b949e' }}>主要: {majorTP}</Text></Col>
                        <Col span={8}><Statistic title="笔" value={ga?.stroke_count || 0} valueStyle={{ fontSize: 14, color: '#e6edf3' }} /></Col>
                        <Col span={8}><Statistic title="线段" value={ga?.segment_count || 0} valueStyle={{ fontSize: 14, color: '#e6edf3' }} /></Col>
                        <Col span={8}><Statistic title="中枢" value={ga?.center_count || 0} valueStyle={{ fontSize: 14, color: '#e6edf3' }} /></Col>
                        <Col span={8}><Statistic title="买卖信号" value={totalSignals} valueStyle={{ fontSize: 14, color: totalSignals > 0 ? '#faad14' : '#8b949e' }} /></Col>
                        <Col span={8}><Statistic title="异常点" value={currentResult.anomalies?.length || 0} valueStyle={{ fontSize: 14, color: highAnomalies > 0 ? '#ff4d4f' : '#8b949e' }} /></Col>
                      </Row>
                    </Card>
                  )}

                  {/* 多周期共振提示 */}
                  {ga?.multi_period_resonance && ga.multi_period_resonance !== 'none' && (
                    <Alert
                      message={
                        ga.multi_period_resonance === 'resonant_up' ? '⚡ 多周期共振向上' :
                        ga.multi_period_resonance === 'resonant_down' ? '⚡ 多周期共振向下' : '🔄 横盘共振'
                      }
                      type={ga.multi_period_resonance === 'resonant_up' ? 'success' : ga.multi_period_resonance === 'resonant_down' ? 'error' : 'info'}
                      showIcon
                      style={{ marginBottom: 12 }}
                    />
                  )}
                </Col>
              </Row>

              {/* ── 底部详情 Tabs ── */}
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
                      label: <span>🔴 拐点分析 ({currentResult.turning_points?.length || 0})</span>,
                      children: (
                        <div>
                          <Space size={8} style={{ marginBottom: 8 }}>
                            <Tag color="red">主要拐点</Tag>
                            <Tag color="orange">中等拐点</Tag>
                            <Tag>次要拐点</Tag>
                          </Space>
                          <Table dataSource={currentResult.turning_points || []} columns={tpColumns}
                            rowKey="index" size="small" pagination={{ pageSize: 15, size: 'small' }}
                            scroll={{ y: 400 }}
                            rowClassName={(r) => r.level === 'major' ? 'chan-major-row' : r.level === 'medium' ? 'chan-medium-row' : ''}
                          />
                        </div>
                      ),
                    },
                    {
                      key: 'signals',
                      label: <span>📶 买卖信号 ({totalSignals})</span>,
                      children: (
                        totalSignals === 0 ? (
                          <Empty description="当前周期未发现明确买卖信号" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        ) : (
                          <Table dataSource={currentResult.signals || []} columns={signalColumns}
                            rowKey={(r, i) => `${r.index}-${r.type}-${i}`}
                            size="small" pagination={{ pageSize: 15, size: 'small' }} scroll={{ y: 400 }}
                          />
                        )
                      ),
                    },
                    {
                      key: 'anomalies',
                      label: <span>⚠️ 异常点 ({currentResult.anomalies?.length || 0})</span>,
                      children: (
                        <div>
                          <Space size={8} style={{ marginBottom: 8 }}>
                            <Badge status="error" text={`高: ${highAnomalies}`} />
                            <Badge status="warning" text={`中: ${currentResult.anomalies?.filter((a: any) => a.severity === 'medium').length || 0}`} />
                          </Space>
                          <Table
                            dataSource={currentResult.anomalies || []}
                            rowKey={(r, i) => `${r.index}-${i}`}
                            size="small"
                            pagination={{ pageSize: 15, size: 'small' }}
                            scroll={{ y: 400 }}
                            columns={[
                              { title: '日期', dataIndex: 'date', width: 100, render: (v: string) => <Text style={{ color: '#8b949e', fontSize: 12 }}>{v}</Text> },
                              { title: '类型', dataIndex: 'type', width: 90, render: (v: string) => {
                                const m: Record<string, { color: string; label: string }> = {
                                  volume_spike: { color: 'volcano', label: '量能异常' },
                                  price_gap: { color: 'purple', label: '价格缺口' },
                                  divergence: { color: 'red', label: '背驰' },
                                  false_break: { color: 'orange', label: '假突破' },
                                  abnormal_range: { color: 'magenta', label: '异常振幅' },
                                };
                                const item = m[v] || { color: 'default', label: v };
                                return <Tag color={item.color}>{item.label}</Tag>;
                              }},
                              { title: '严重度', dataIndex: 'severity', width: 60, render: (v: string) => <Badge status={v === 'high' ? 'error' : v === 'medium' ? 'warning' : 'default'} text={v === 'high' ? '高' : '中'} /> },
                              { title: '描述', dataIndex: 'description', render: (v: string) => <Text style={{ color: '#c9d1d9', fontSize: 12 }}>{v}</Text> },
                            ]}
                          />
                        </div>
                      ),
                    },
                    {
                      key: 'structure',
                      label: '📐 结构树',
                      children: (
                        <Collapse
                          ghost
                          items={[
                            {
                              key: 'centers',
                              label: <Text style={{ color: '#e6edf3' }}>中枢列表 ({currentResult.centers?.length || 0})</Text>,
                              children: (
                                <Table dataSource={currentResult.centers || []} rowKey="start_index" size="small" pagination={{ pageSize: 10, size: 'small' }}
                                  columns={[
                                    { title: '上轨ZG', dataIndex: 'zg', render: (v: number) => <Text style={{ color: '#ff4d4f' }}>{v}</Text> },
                                    { title: '下轨ZD', dataIndex: 'zd', render: (v: number) => <Text style={{ color: '#52c41a' }}>{v}</Text> },
                                    { title: '中轴', dataIndex: 'zz' }, { title: '级别', dataIndex: 'level' },
                                    { title: '起始', dataIndex: 'start_date', render: (v: string) => <Text style={{ fontSize: 11 }}>{v}</Text> },
                                    { title: '结束', dataIndex: 'end_date', render: (v: string) => <Text style={{ fontSize: 11 }}>{v}</Text> },
                                    { title: '强度', dataIndex: 'strength' }, { title: 'K线数', dataIndex: 'kline_count' },
                                  ]}
                                />
                              ),
                            },
                            {
                              key: 'strokes',
                              label: <Text style={{ color: '#e6edf3' }}>笔的列表 ({currentResult.strokes?.length || 0})</Text>,
                              children: (
                                <Table dataSource={currentResult.strokes || []} rowKey="start_index" size="small" pagination={{ pageSize: 10, size: 'small' }}
                                  columns={[
                                    { title: '方向', dataIndex: 'direction', width: 50, render: (v: string) => <Tag color={v === 'up' ? 'red' : 'green'}>{v === 'up' ? '↑' : '↓'}</Tag> },
                                    { title: '起点', dataIndex: 'start_date', width: 90 }, { title: '终点', dataIndex: 'end_date', width: 90 },
                                    { title: '起价', dataIndex: 'start_price', width: 70 }, { title: '终价', dataIndex: 'end_price', width: 70 },
                                    { title: '力度%', dataIndex: 'strength', width: 60, render: (v: number) => `${v}%` },
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
            </>
          )}

          {/* ── 多周期联立 Tab 内容 ── */}
          {activeGroup === 'overview' && (
            <>{renderMultiPeriodOverview()}</>
          )}
        </>
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
