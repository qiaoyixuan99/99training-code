# 📊 QuantTrading Workstation — 一体化量化交易辅助平台

> 集行情看盘、智能选股、缠论分析、策略回测于一体的桌面量化交易工作站

---

## 🎯 产品定位

自主打造的一体化量化交易辅助软件，彻底解决传统量化、看盘选股操作繁琐的痛点。
**核心特色：功能集成化** — 行情看盘、智能选股、策略回测三大核心模块融合在同一界面。

---

## 🏗️ 项目结构

```
quant-trading-workstation/
│
├── desktop/                          # 🖥️ Electron + React 桌面前端
│   ├── electron/                     # Electron 主进程
│   │   ├── main.ts                   # 主进程入口
│   │   ├── preload.ts                # 预加载脚本
│   │   └── ipc/                      # IPC 通信模块
│   │
│   ├── src/                          # React 渲染进程
│   │   ├── components/               # 通用 UI 组件
│   │   │   ├── KLineChart/           # K线图表组件 (TradingView lightweight)
│   │   │   ├── StrategyEditor/       # 策略代码编辑器 (Monaco Editor)
│   │   │   ├── BacktestPanel/        # 回测结果面板
│   │   │   ├── StockScreener/        # 选股筛选器
│   │   │   ├── ChanTheoryBoard/      # 缠论标注面板
│   │   │   ├── MomentumGauge/        # 动能评分仪表盘
│   │   │   └── MarketTimingIndicator/# 大盘择时指标
│   │   │
│   │   ├── pages/                    # 页面
│   │   │   ├── dashboard/            # 📈 行情看盘（主页面）
│   │   │   ├── stock-screener/       # 🔍 智能选股
│   │   │   ├── backtest/             # ⚡ 回测中心
│   │   │   ├── strategy-editor/      # ✏️ 策略编辑器
│   │   │   ├── chan-theory/          # 🧠 缠论分析
│   │   │   ├── market-timing/        # 🎯 大盘择时
│   │   │   └── settings/             # ⚙️ 系统设置
│   │   │
│   │   ├── services/                 # API 调用层
│   │   ├── stores/                   # 状态管理 (Zustand)
│   │   └── utils/                    # 工具函数
│   │
│   └── package.json
│
├── server/                           # 🐍 Python FastAPI 后端
│   ├── main.py                       # 服务入口
│   ├── config/                       # 配置文件
│   │   ├── settings.py               # 全局配置
│   │   └── data_sources.py           # 数据源配置
│   │
│   ├── api/                          # API 路由层
│   │   └── routes/
│   │       ├── market_data.py        # 行情数据接口
│   │       ├── screening.py          # 选股接口
│   │       ├── backtest.py           # 回测接口
│   │       ├── strategy.py           # 策略管理接口
│   │       ├── chan_theory.py        # 缠论分析接口
│   │       ├── momentum.py           # 动能评分接口
│   │       ├── timing.py             # 大盘择时接口
│   │       └── watchlist.py          # 自选股接口
│   │
│   ├── core/                         # 核心计算引擎
│   │   ├── data_engine/              # 数据引擎
│   │   │   ├── fetcher.py            # 数据获取 (AKShare/Baostock, 分时+日线)
│   │   │   ├── cleaner.py            # 数据清洗
│   │   │   └── cache.py              # 数据缓存
│   │   │
│   │   ├── chan_engine/              # 缠论引擎 ⭐ (完整实现)
│   │   │   ├── fractal.py            # 顶底分型识别 + K线包含处理
│   │   │   ├── stroke.py             # 笔的划分 + 方向交替验证
│   │   │   ├── segment.py            # 线段构建 + 线段背驰检测
│   │   │   ├── center.py             # 中枢识别 (ZG/ZD/ZZ) + 引力分析
│   │   │   ├── buy_sell_point.py     # 一二三类买卖点判定 (MACD背驰)
│   │   │   └── chan_analyzer.py      # 多维度综合分析器 (全局+局部+拐点+异常)
│   │   │
│   │   ├── screening_engine/         # 选股引擎
│   │   │   ├── fundamental_filter.py # 基本面过滤
│   │   │   ├── technical_filter.py   # 技术面过滤
│   │   │   ├── scorer.py             # 多因子打分
│   │   │   └── ranker.py             # 排序器
│   │   │
│   │   ├── backtest_engine/          # 回测引擎 ⚡
│   │   │   ├── vectorized_bt.py      # 向量化回测 (高性能核心)
│   │   │   ├── event_driven_bt.py    # 事件驱动回测
│   │   │   ├── metrics.py            # 绩效指标计算
│   │   │   └── report.py             # 回测报告生成
│   │   │
│   │   ├── timing_engine/            # 择时引擎
│   │   │   ├── trend_analyzer.py     # 趋势分析
│   │   │   ├── breadth_analyzer.py   # 市场宽度分析
│   │   │   └── signal_generator.py   # 信号生成
│   │   │
│   │   ├── momentum_engine/          # 动能评分引擎
│   │   │   ├── price_momentum.py     # 价格动能
│   │   │   ├── volume_momentum.py    # 量能动能力
│   │   │   └── composite_score.py    # 综合评分
│   │   │
│   │   └── risk_engine/              # 风控引擎
│   │       ├── position_sizer.py     # 仓位计算
│   │       └── risk_metrics.py       # 风险指标
│   │
│   ├── models/                       # 数据模型
│   │   ├── stock.py                  # 股票模型
│   │   ├── strategy.py               # 策略模型
│   │   ├── backtest.py               # 回测记录模型
│   │   └── watchlist.py              # 自选股模型
│   │
│   ├── schemas/                      # Pydantic 数据校验
│   └── requirements.txt
│
├── strategies/                       # 📝 用户自定义策略存放目录
│   ├── examples/                     # 示例策略
│   │   ├── ma_cross.py               # 双均线交叉
│   │   ├── chan_theory_strategy.py   # 缠论策略
│   │   └── momentum_breakout.py      # 动量突破
│   └── my_strategies/                # 用户策略
│
├── data/                             # 💾 本地数据存储
│   ├── market/                       # 行情数据 (Parquet 格式)
│   ├── financial/                    # 财务数据
│   └── indicators/                   # 指标缓存
│
└── docs/                             # 📚 文档
    ├── ARCHITECTURE.md               # 架构设计文档
    ├── TASK_LIST.md                  # 任务清单
    ├── DATA_SOURCES.md               # 数据源与数据库方案
    └── ALGORITHMS.md                 # 算法说明
```

---

## 🔧 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| **桌面框架** | Electron 28+ | 跨平台桌面应用壳 |
| **前端 UI** | React 18 + TypeScript | 组件化 UI 开发 |
| **K线图表** | TradingView Lightweight Charts | 专业金融图表渲染 |
| **代码编辑器** | Monaco Editor | VS Code 同款编辑器内核 |
| **状态管理** | Zustand | 轻量级 React 状态管理 |
| **UI 组件库** | Ant Design 5 | 企业级 UI 组件 |
| **后端框架** | FastAPI (Python 3.11+) | 高性能异步 API |
| **科学计算** | NumPy + Pandas + Numba | 向量化加速计算 |
| **技术指标** | TA-Lib + Custom | 技术指标计算 |
| **机器学习** | Scikit-learn + XGBoost + PyTorch | 预测模型 |
| **数据库** | SQLite + Parquet + Redis | 本地化存储方案 |
| **数据源** | AKShare + Tushare + Baostock | A股数据获取 |
| **回测引擎** | 自研向量化引擎 | 300只/3分钟高性能 |

---

## 🚀 快速开始

```bash
# 1. 启动后端服务
cd server
pip install -r requirements.txt
python main.py              # 启动在 http://localhost:8000

# 2. 启动桌面应用
cd desktop
npm install
npm run dev                 # 开发模式启动 Electron + React

# 3. 打包发布
npm run build               # 打包为 exe/dmg/AppImage
```

---

## 📋 核心功能模块

| 模块 | 功能 | 进度 |
|------|------|------|
| 📈 行情看盘 | 多周期K线(分时/日/周/月)、实时行情、自选股管理 | ✅ 已完成 |
| 🔍 智能选股 | 基本面过滤 + 技术面筛选 + 多因子排序 | 🚧 骨架搭建 |
| ⚡ 策略回测 | 向量化回测、夏普比率、胜率、最大回撤 | 🚧 骨架搭建 |
| ✏️ 策略编辑器 | Monaco 代码编辑器、语法高亮、自动补全 | 规划中 |
| 🧠 缠论分析 | 分型→笔→线段→中枢→买卖点自动标注 + 多维度分析 | ✅ 已完成 |
| 🎯 大盘择时 | 趋势判断、市场宽度、买卖信号 | 规划中 |
| 📊 动能评分 | 价格动能 + 量能动能综合评分 | 规划中 |
| 🛡️ 风控模块 | 仓位管理、止损止盈、风险指标 | 规划中 |

---

## 🎓 使用门槛

- **普通股民**：直接使用看盘、选股、缠论标注等现成功能
- **量化从业者**：自主编写策略 → 回测验证 → 实盘辅助决策
- **编程基础**：策略编写需掌握 Python 基础 + 量化逻辑
- **硬件要求**：普通电脑即可运行，无需额外安装多款软件
