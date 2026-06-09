# AI 量化分析引擎

> Python Flask API 服务器 — 为微信小程序提供 K 线技术分析能力

## 快速启动

```bash
pip install -r requirements.txt
python server.py                    # 默认 http://127.0.0.1:5000
python server.py --port 8080        # 自定义端口
python server.py --host 0.0.0.0     # 局域网访问（手机调试）
```

## API 文档

### `GET /api/health`
健康检查，返回引擎状态、已加载策略和预测器数量。

### `POST /api/analyze`
综合分析 — 引擎自行从东方财富获取 K 线数据后分析。

```json
// Request
{ "code": "000001", "period": "day", "count": 200 }

// Response
{ "success": true, "data": { ... 完整分析报告 ... } }
```

### `POST /api/analyze_data` ⭐ 推荐
K 线数据分析 — 小程序端获取数据后直传，绕过 Python→东方财富 SSL 兼容问题。

```json
// Request
{
  "code": "000001",
  "period": "day",
  "klines": [{ "time": "2026-06-09", "open": 10.0, "close": 10.5, ... }],
  "stock_name": "平安银行",
  "latest_price": 11.03,
  "latest_change_pct": 1.25
}
```

### `POST /api/analyze_simple`
轻量分析摘要，适合列表页快速展示。

### `POST /api/quote`
实时行情快照。

### `POST /api/search`
股票搜索（代码/名称模糊匹配）。

## 命令行使用

```bash
python main.py 000001 day           # 终端彩色表格输出
python main.py 000001 day --json    # JSON 格式
python main.py 300750 60min         # 60分钟K线分析
```

## 核心模块

| 模块 | 说明 |
|------|------|
| `core/data.py` | 东方财富 API 封装 + KlineBar/QuoteSnapshot 数据类 |
| `core/indicators.py` | 技术指标（MA/MACD/RSI/布林带/KDJ/ATR/量价分析） |
| `core/patterns.py` | K 线形态识别（十字星/锤子/吞没/支撑压力/趋势判断） |
| `core/analyzer.py` | 综合分析编排引擎（KlineAnalyzer） |
| `interfaces/strategy.py` | Strategy ABC + StrategyRegistry（可插拔策略接口） |
| `interfaces/predictor.py` | Predictor ABC + PredictorRegistry（可插拔预测接口） |
| `output/formatter.py` | JSON / 终端表格输出 |

## 可插拔接口

### 添加新策略

```python
from interfaces.strategy import BaseStrategy, StrategyResult, Signal

class MyStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "我的策略"

    @property
    def description(self) -> str:
        return "自定义交易策略"

    def analyze(self, klines, indicators) -> StrategyResult:
        # 分析逻辑
        return StrategyResult(
            strategy=self.name,
            signals=[Signal(type='buy', strength=7, price=klines[-1].close, reason='...')],
            confidence=0.75,
            reason='...',
        )

# 注册
analyzer.strategies.register(MyStrategy())
```

### 添加新预测模型

```python
from interfaces.predictor import BasePredictor, PredictionResult

class MyPredictor(BasePredictor):
    @property
    def name(self) -> str:
        return "我的预测模型"

    @property
    def description(self) -> str:
        return "自定义预测"

    def predict(self, klines, indicators) -> PredictionResult:
        return PredictionResult(
            predictor=self.name,
            direction='up',
            target_price=15.0,
            confidence=0.6,
            horizon=5,
            reason='...',
        )
```

## 技术指标说明

| 指标 | 函数 | 说明 |
|------|------|------|
| MA | `ma(klines, period)` | 简单移动平均 |
| EMA | `ema(klines, period)` | 指数移动平均 |
| MACD | `macd(klines)` | MACD (DIF/DEA/柱) |
| RSI | `rsi(klines, period)` | 相对强弱指标 |
| 布林带 | `bollinger(klines)` | 上轨/中轨/下轨 |
| KDJ | `kdj(klines)` | 随机指标 |
| ATR | `atr(klines)` | 平均真实波幅 |
| 量价 | `volume_profile(klines)` | POC + 价值区域 + 量比 |

## 数据源

- K 线历史：东方财富 `push2his.eastmoney.com`
- 实时行情：东方财富 `push2.eastmoney.com`
- 股票搜索：东方财富 `searchadapter.eastmoney.com`

> ⚠️ Windows 环境下 Python 请求东方财富 API 可能存在 schannel TLS 兼容问题。已通过 `verify=False` + `requests.Session` 绕过。推荐使用 `/api/analyze_data` 端点（小程序端获取数据）。

## 免责声明

⚠️ 本引擎仅供学习研究。分析结果不构成任何投资建议。
