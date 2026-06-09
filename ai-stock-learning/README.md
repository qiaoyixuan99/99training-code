# 📈 AI K线量化分析系统

> K线技术分析引擎 + 微信小程序前端 — 可插拔策略/预测接口，支持拐点检测与AI分析

---

## 项目结构

```
ai-stock-learning/
├── ai-engine/                 # Python 量化分析引擎
│   ├── server.py              # Flask API 服务器（小程序后端）
│   ├── main.py                # CLI 命令行入口
│   ├── requirements.txt       # Python 依赖
│   ├── core/                  # 核心分析模块
│   │   ├── data.py            #   东方财富 API 封装 + K线数据类
│   │   ├── indicators.py      #   技术指标（MA/MACD/RSI/布林/KDJ/ATR/量价）
│   │   ├── patterns.py        #   K线形态识别（十字星/锤子/吞没/支撑压力/趋势）
│   │   └── analyzer.py        #   综合分析编排引擎
│   ├── interfaces/            # 可插拔接口（ABC 抽象基类）
│   │   ├── strategy.py        #   交易策略接口 + 注册中心
│   │   └── predictor.py       #   预测模型接口 + 注册中心
│   └── output/                # 输出格式化
│       └── formatter.py       #   JSON / 终端表格输出
│
├── miniapp/                   # 微信小程序前端
│   ├── app.js / app.json      # 全局配置（4 TabBar）
│   ├── pages/
│   │   ├── chart/             #   📈 K线图表页（Canvas 2D + 拐点标记 + 搜索）
│   │   ├── analysis/          #   🔍 AI 分析页（引擎分析 + 本地降级）
│   │   ├── watchlist/         #   ⭐ 自选股列表
│   │   └── profile/           #   👤 个人中心 + 分析历史
│   ├── services/
│   │   ├── ai-engine.js       #   对接 Python Flask API
│   │   └── market-data.js     #   东方财富行情 API（wx.request）
│   └── utils/
│       └── turning-points.js  #   拐点检测算法（局部极值 + 强度评分）
│
├── docs/                      # 项目文档
│   ├── BLUEPRINT.md           #   原始产品蓝图（学习小程序方案）
│   └── PROGRESS.md            #   开发进度
│
└── knowledge-base/            # 知识库目录（预留，待建设）
```

---

## 快速开始

### 1. 启动 Python 分析引擎

```bash
cd ai-engine
pip install -r requirements.txt
python server.py                  # 默认 http://127.0.0.1:5000
```

API 端点：
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/analyze` | 综合分析（引擎自行获取K线数据） |
| POST | `/api/analyze_data` | K线数据分析（小程序直传数据，推荐） |
| POST | `/api/analyze_simple` | 轻量分析摘要 |
| POST | `/api/quote` | 实时行情快照 |
| POST | `/api/search` | 股票搜索 |

### 2. 打开微信小程序

1. 打开 **微信开发者工具**
2. 导入项目 → 选择 `miniapp/` 目录
3. AppID：`wx9f087668ad188582`（或使用测试号）
4. 设置 → 不校验合法域名（本地调试）

### 3. 命令行使用

```bash
cd ai-engine
python main.py 000001 day        # 平安银行日K分析（终端表格输出）
python main.py 000001 day --json  # JSON 格式输出
```

---

## 架构设计

```
微信小程序 (wx.request)
    │ 获取K线数据（东方财富API）
    ▼
Flask API Server (/api/analyze_data)
    │
    ▼
KlineAnalyzer 编排引擎
    ├── compute_all_indicators()   → MA/MACD/RSI/布林/KDJ/ATR/量价
    ├── detect_all_patterns()      → 形态识别 + 趋势判断 + 支撑压力
    ├── Strategy[].analyze()       → 已注册策略分析（可插拔）
    └── Predictor[].predict()      → 已注册预测模型（可插拔）
    │
    ▼
结构化 JSON 报告 → 小程序渲染
```

### 可插拔接口

**策略接口** (`interfaces/strategy.py`)：
```python
class BaseStrategy(ABC):
    name: str
    description: str
    def analyze(klines, indicators) -> StrategyResult
```

**预测接口** (`interfaces/predictor.py`)：
```python
class BasePredictor(ABC):
    name: str
    description: str
    def predict(klines, indicators) -> PredictionResult
```

后续添加策略/预测模型只需：继承基类 → 实现方法 → 注册到 Registry。

---

## 支持的功能

| 功能 | 状态 |
|------|------|
| 东方财富行情数据获取 | ✅ |
| K线图表（Canvas 2D）+ 多周期切换 | ✅ |
| 技术指标计算（MA/MACD/RSI/布林/KDJ/ATR） | ✅ |
| K线形态识别（十字星/锤子/吞没/趋势/支撑压力） | ✅ |
| 拐点自动检测 + 强度评分 | ✅ |
| AI 综合分析报告 | ✅ |
| 自选股管理 | ✅ |
| 策略接口（ABC，可插拔） | ✅ |
| 预测接口（ABC，可插拔） | ✅ |
| 具体交易策略实现 | ❌（用户自行扩展） |
| ML 预测模型接入 | ❌（用户自行扩展） |

---

## 数据源

- **K线历史**：东方财富 push2his API
- **实时行情**：东方财富 push2 API
- **股票搜索**：东方财富 searchadapter API

> ⚠️ Windows Python 环境下东方财富 API 可能存在 SSL/TLS 兼容问题，建议使用 `/api/analyze_data` 端点（小程序端获取数据 → 发送到引擎分析）。

---

## 免责声明

⚠️ 本项目仅供学习研究使用，所有分析结果不构成任何投资建议。投资有风险，入市需谨慎。
