# 🏗️ 架构设计文档 — QuantTrading Workstation

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                   Electron Desktop Shell                  │
│  ┌───────────────────────────────────────────────────┐  │
│  │              React SPA (Renderer Process)          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │Dashboard │ │Screener  │ │Backtest Center   │  │  │
│  │  │ 行情看盘  │ │ 智能选股  │ │ 策略回测中心      │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │ChanTheory│ │Strategy  │ │Market Timing     │  │  │
│  │  │ 缠论分析  │ │ 策略编辑  │ │ 大盘择时          │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └───────────────────┬───────────────────────────────┘  │
│                      │ HTTP + WebSocket                  │
│  ┌───────────────────┴───────────────────────────────┐  │
│  │              Python FastAPI Server                  │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │              API Layer (REST + WS)            │  │  │
│  │  ├──────────┬──────────┬──────────┬─────────────┤  │  │
│  │  │Market API│Screen API│Bt API    │Chan API     │  │  │
│  │  ├──────────┴──────────┴──────────┴─────────────┤  │  │
│  │  │            Service Layer                       │  │  │
│  │  ├──────────────────────────────────────────────┤  │  │
│  │  │            Core Engine Layer                   │  │  │
│  │  │ ┌────────┐┌────────┐┌────────┐┌───────────┐ │  │  │
│  │  │ │Data    ││Chan    ││Backtest││Momentum   │ │  │  │
│  │  │ │Engine  ││Engine  ││Engine  ││Engine      │ │  │  │
│  │  │ └────────┘└────────┘└────────┘└───────────┘ │  │  │
│  │  │ ┌────────┐┌────────┐┌────────┐              │  │  │
│  │  │ │Screen  ││Timing  ││Risk    │              │  │  │
│  │  │ │Engine  ││Engine  ││Engine  │              │  │  │
│  │  │ └────────┘└────────┘└────────┘              │  │  │
│  │  ├──────────────────────────────────────────────┤  │  │
│  │  │            Data Layer                         │  │  │
│  │  │ ┌──────────┐ ┌────────┐ ┌────────────────┐  │  │  │
│  │  │ │ SQLite   │ │Parquet │ │ Redis (Cache)  │  │  │  │
│  │  │ │(元数据)  │ │(行情)   │ │ (实时缓存)     │  │  │  │
│  │  │ └──────────┘ └────────┘ └────────────────┘  │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 前端架构 (Electron + React)

### 2.1 技术选型理由

| 需求 | 方案 | 理由 |
|------|------|------|
| 跨平台桌面应用 | Electron 28 | Win/Mac/Linux 一次开发，生态成熟 |
| K线图表渲染 | Lightweight Charts (TradingView) | 专业级金融图表，Canvas渲染性能优异 |
| 策略代码编辑 | Monaco Editor | VSCode内核，语法高亮+自动补全 |
| 状态管理 | Zustand | 比Redux轻量，TypeScript友好 |
| UI组件 | Ant Design 5 | 中后台最优选择，表格/表单能力强大 |
| 构建工具 | Vite 5 | 秒级HMR，开发体验极佳 |

### 2.2 页面路由设计

```
/                        → 重定向到 /dashboard
/dashboard               → 行情看盘（主页面）
  左侧: 自选股列表 + 市场概览
  中间: K线图区域 (多周期切换)
  右侧: 缠论标注 + 动能评分面板
/screener                → 智能选股
  顶部: 筛选条件配置
  中间: 选股结果表格
  底部: 个股详情弹窗
/backtest                → 回测中心
  左侧: 策略选择 + 参数配置
  中间: 回测进度 + 资金曲线图
  右侧: 绩效指标面板
/strategy-editor         → 策略编辑器
  左侧: 文件树
  中间: Monaco代码编辑器
  右侧: 策略参数面板
/chan-theory             → 缠论专项分析
  全屏K线 + 缠论标注
  笔/线段/中枢 图层切换
/market-timing           → 大盘择时
  指数K线 + 择时信号标注
  市场宽度指标面板
/settings                → 系统设置
  数据源配置 / 策略路径 / 界面偏好
```

### 2.3 核心组件设计

```typescript
// KLineChart 组件接口
interface KLineChartProps {
  symbol: string;           // 股票代码
  period: '1m'|'5m'|'15m'|'30m'|'60m'|'1d'|'1w'|'1M'; // 多周期
  overlays: {               // 叠加图层
    chanTheory?: ChanOverlay;   // 缠论标注层
    indicators?: Indicator[];   // 技术指标层
    signals?: Signal[];         // 交易信号层
  };
  onPeriodChange: (p: Period) => void;
}

// StrategyEditor 组件接口
interface StrategyEditorProps {
  code: string;
  language: 'python';
  onSave: (code: string) => void;
  onBacktest: (code: string, params: BacktestParams) => void;
}

// BacktestPanel 组件接口
interface BacktestPanelProps {
  result: BacktestResult;
  // { equityCurve, sharpeRatio, winRate, maxDrawdown, annualReturn, ... }
}
```

---

## 3. 后端架构 (Python FastAPI)

### 3.1 引擎层详细设计

```
server/core/
│
├── data_engine/            # 数据引擎 — 所有数据的统一入口
│   ├── fetcher.py          # 多数据源适配器
│   │   ├── AKShareAdapter   # 免费A股数据
│   │   ├── TushareAdapter   # Tushare Pro数据
│   │   └── BaostockAdapter  # 证券宝数据
│   ├── cleaner.py          # 数据清洗管道
│   │   ├── 复权处理
│   │   ├── 停牌标记
│   │   └── 异常值过滤
│   └── cache.py            # 多级缓存
│       ├── L1: Redis (实时数据)
│       ├── L2: Parquet文件 (历史数据)
│       └── L3: SQLite (元数据索引)
│
├── chan_engine/            # 缠论引擎 ⭐核心算法模块
│   ├── fractal.py          # 顶底分型识别
│   │   └── 算法: K线包含处理 → 顶分型/底分型判定
│   ├── stroke.py           # 笔的划分
│   │   └── 算法: 分型间连线 → 笔的确认规则
│   ├── segment.py          # 线段构建
│   │   └── 算法: 笔的包含处理 → 线段终结判断
│   ├── center.py           # 中枢识别
│   │   └── 算法: 连续重叠区间 → 中枢ZG/ZD计算
│   └── buy_sell_point.py   # 买卖点判定
│       ├── 第一类买卖点 (趋势背驰)
│       ├── 第二类买卖点 (回抽确认)
│       └── 第三类买卖点 (中枢破坏)
│
├── backtest_engine/        # 回测引擎 ⚡性能核心
│   ├── vectorized_bt.py    # 向量化回测 (主力引擎)
│   │   ├── 基于NumPy/Numba的矢量化计算
│   │   ├── 300只股票 < 3分钟
│   │   └── 支持: 止损/止盈/滑点/手续费
│   ├── event_driven_bt.py  # 事件驱动回测 (精确回测)
│   └── metrics.py          # 绩效指标
│       ├── 夏普比率 (Sharpe Ratio)
│       ├── 胜率 (Win Rate)
│       ├── 最大回撤 (Max Drawdown)
│       ├── 年化收益率 (Annual Return)
│       ├── 盈亏比 (Profit/Loss Ratio)
│       ├── 卡尔玛比率 (Calmar Ratio)
│       └── 信息比率 (Information Ratio)
│
├── screening_engine/       # 选股引擎
│   ├── fundamental_filter.py
│   │   ├── PE/PB/PS 估值过滤
│   │   ├── ROE/ROA 盈利能力过滤
│   │   ├── 营收/利润增长率过滤
│   │   └── 市值/行业分类过滤
│   ├── technical_filter.py
│   │   ├── 均线系统过滤 (MA多头排列)
│   │   ├── MACD/KDJ/RSI 信号过滤
│   │   └── 成交量异常检测
│   ├── scorer.py           # 多因子打分
│   │   └── 等权/IC加权/动态权重
│   └── ranker.py           # 排序输出
│
├── timing_engine/          # 择时引擎
│   ├── trend_analyzer.py   # 趋势判断
│   │   ├── 多周期均线共振
│   │   ├── ADX 趋势强度
│   │   └── 布林带位置
│   ├── breadth_analyzer.py # 市场宽度
│   │   ├── 涨跌家数比
│   │   ├── 新高新低比
│   │   └── 行业轮动热度
│   └── signal_generator.py # 综合信号
│       └── 多指标投票/加权
│
├── momentum_engine/        # 动能评分引擎
│   ├── price_momentum.py   # 价格动能
│   │   ├── 多周期收益率
│   │   ├── RSI 相对强弱
│   │   └── 价格相对均线位置
│   ├── volume_momentum.py  # 量能动能
│   │   ├── 量比分析
│   │   ├── OBV 能量潮
│   │   └── 资金流向
│   └── composite_score.py  # 综合评分 (0-100分)
│
└── risk_engine/            # 风控引擎
    ├── position_sizer.py   # 仓位计算
    │   ├── Kelly公式
    │   ├── 固定比例
    │   └── ATR波动率调整
    └── risk_metrics.py     # 风险监控
        ├── VaR (风险价值)
        └── CVaR (条件风险价值)
```

### 3.2 API 设计

```
GET    /api/v1/market/kline/{symbol}?period=1d&limit=500    # K线数据
GET    /api/v1/market/realtime/{symbol}                       # 实时行情
GET    /api/v1/market/index/{index_code}                      # 指数行情

POST   /api/v1/screener/run                                  # 执行选股
GET    /api/v1/screener/conditions                            # 可选筛选条件

POST   /api/v1/backtest/run                                  # 执行回测
GET    /api/v1/backtest/result/{task_id}                      # 回测结果
GET    /api/v1/backtest/history                               # 历史回测记录

POST   /api/v1/chan-theory/analyze/{symbol}                   # 缠论分析
GET    /api/v1/chan-theory/points/{symbol}                    # 买卖点列表

POST   /api/v1/momentum/score/{symbol}                        # 动能评分
POST   /api/v1/timing/signal                                  # 大盘择时信号

GET    /api/v1/strategy/list                                  # 策略列表
POST   /api/v1/strategy/save                                 # 保存策略
POST   /api/v1/strategy/validate                             # 策略语法校验

WS     /ws/market/realtime                                    # 实时行情推送
```

---

## 4. 数据流设计

```
[数据源 AKShare/Tushare/Baostock]
         │
         ▼
[Data Engine - fetcher.py]  ← 定时任务 / 手动触发
         │
         ├──→ Parquet 文件 (历史行情, 列式存储, 快速读取)
         ├──→ Redis (实时报价, 60s TTL)
         └──→ SQLite (股票元信息, 自选股, 策略记录, 回测记录)
         │
         ▼
[Core Engines]  ← 按需加载 Parquet → Pandas DataFrame → 向量化计算
         │
         ▼
[FastAPI Routes]  ← JSON Response
         │
         ▼
[React Frontend]  ← Zustand Store → UI 渲染
```

---

## 5. 性能设计

### 5.1 回测性能目标：300只股票 × 全历史 < 3分钟

```
优化策略:
1. Parquet 列式存储 → 只读取需要的列 (OHLCV)
2. NumPy 向量化计算 → 避免 Python for 循环
3. Numba JIT 编译 → 热点函数加速 10-100x
4. 多进程并行 → 每只股票独立计算，Pool.map
5. 预计算指标缓存 → 常用指标提前计算存储
```

### 5.2 K线渲染性能

```
TradingView Lightweight Charts:
- Canvas 渲染，万级别数据点无压力
- 按需加载：可视范围外数据不渲染
- 数据下采样：缩小时自动聚合
```
