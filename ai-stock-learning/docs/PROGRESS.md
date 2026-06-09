# 🚀 AI K线量化分析系统 — 开发进度

> 最后更新：2026-06-09 | 状态：**MVP 完成，可运行**

---

## 产品定位

**K线量化分析系统** — Python AI 引擎 + 微信小程序前端，可插拔策略/预测接口。

---

## 已完成文件清单

### Python 引擎 (9 files)

| 文件 | 说明 |
|------|------|
| `ai-engine/server.py` | Flask API 服务器（6个端点） |
| `ai-engine/main.py` | CLI 命令行入口 |
| `ai-engine/requirements.txt` | Python 依赖 |
| `ai-engine/core/data.py` | 东方财富 API 封装 + KlineBar 数据类 |
| `ai-engine/core/indicators.py` | 技术指标（MA/MACD/RSI/布林/KDJ/ATR/量价） |
| `ai-engine/core/patterns.py` | K线形态识别 + 趋势判断 + 支撑压力 |
| `ai-engine/core/analyzer.py` | 综合分析编排引擎（KlineAnalyzer） |
| `ai-engine/interfaces/strategy.py` | Strategy ABC + StrategyRegistry |
| `ai-engine/interfaces/predictor.py` | Predictor ABC + PredictorRegistry |
| `ai-engine/output/formatter.py` | JSON/终端表格输出 |

### 微信小程序 (4 pages + 2 services + 1 util)

| 页面/模块 | 说明 |
|-----------|------|
| `pages/chart/` | Canvas 2D K线图 + 拐点标记 + 搜索 |
| `pages/analysis/` | AI 综合分析（引擎优先 → 本地降级） |
| `pages/watchlist/` | 自选股管理 |
| `pages/profile/` | 个人中心 + 分析历史 |
| `services/market-data.js` | 东方财富数据接口 |
| `services/ai-engine.js` | Python Flask API 对接 |
| `utils/turning-points.js` | 拐点检测算法 |

---

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/analyze` | 综合分析（引擎获取数据） |
| POST | `/api/analyze_data` | 分析（小程序直传K线数据，推荐）|
| POST | `/api/analyze_simple` | 轻量摘要 |
| POST | `/api/quote` | 实时行情 |
| POST | `/api/search` | 股票搜索 |

---

## 已知问题与修复记录

| 问题 | 状态 | 说明 |
|------|------|------|
| Python→东方财富 SSL 连接失败 | ✅ 已修复 | 使用 `verify=False` + `requests.Session`；新增 `/api/analyze_data` 端点绕过 |
| indicators.py 重复 ATR 计算 | ✅ 已修复 | `atr_last` 计算一次，复用 |
| Flask 500 错误 | ✅ 已修复 | 多层 fallback 架构 |
| 小程序空白页面 | ⚠️ 待排查 | 编译成功但页面数据为空，可能 Canvas 2D 初始化问题 |

---

## 核心算法

### 技术指标
- MA (SMA/EMA) — 5/10/20/60 周期
- MACD — DIF/DEA/柱状图
- RSI — 6/14/24 周期
- 布林带 — 20 周期 ±2σ
- KDJ — 9/3/3 参数
- ATR — 14 周期平均真实波幅
- 量价分析 — POC + 70% 价值区域

### 形态识别
- 十字星 / 长腿十字星 / 墓碑十字
- 锤子线 / 倒锤子
- 吞没形态（看涨/看跌）
- 支撑/压力位（局部极值聚类）
- 趋势判断（均线排列 + 价格位置综合评分）

### 拐点检测（小程序端）
```
1. 局部极值扫描 → 找峰/谷
2. 距离合并 → 过滤噪音
3. 强度评分 (1-10) → 振幅/成交量/影线/趋势幅度
4. 分类标注 → 主要顶底/阶段高点低点/短顶短底
5. 趋势关联 → 拐点间涨跌幅、持续天数
```

---

## 架构亮点

### 可插拔设计
- **Strategy ABC**：继承 `BaseStrategy` → 实现 `analyze()` → 注册到 `StrategyRegistry`
- **Predictor ABC**：继承 `BasePredictor` → 实现 `predict()` → 注册到 `PredictorRegistry`
- 后续可接入 LSTM/XGBoost/LLM 等预测模型

### 多层降级
```
小程序 analysis 页面
  ├── 1. ping 引擎 → /api/analyze_data（K线直传）✅ 推荐
  ├── 2. 失败 → /api/analyze（引擎自行获取）🔄 fallback 1
  └── 3. 失败 → 本地分析（turning-points.js）🔄 fallback 2
```

---

## 下一步计划

| 优先级 | 功能 | 说明 |
|--------|------|------|
| 🔴 高 | 排查小程序空白页面问题 | Canvas 2D 初始化失败 |
| 🔴 高 | 实现至少一个示例策略 | 验证 Strategy 接口可扩展性 |
| 🟡 中 | ECharts 版图表替代 Canvas 2D | 更丰富的交互体验 |
| 🟡 中 | 历史回测功能 | 验证拐点信号准确率 |
| 🟢 低 | 拐点推送通知 | 订阅消息 |
| 🟢 低 | H5 版适配 | 微信外分享 |
