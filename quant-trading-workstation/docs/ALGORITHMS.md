# 🧠 算法说明 — QuantTrading Workstation

---

## 1. 缠论引擎 (Chan Theory Engine)

### 1.1 算法流程

```
原始K线 → 包含处理 → 顶底分型 → 笔 → 线段 → 中枢 → 买卖点
  │          │          │        │      │       │        │
  │   合并相邻包含 找局部极值  连接分型  笔的升级  重叠区间  背驰判断
```

### 1.2 各步骤算法详解

#### (1) K线包含处理

```
规则：相邻两根K线存在包含关系时（一根的高低点完全包含另一根）
- 上升趋势中：取高高(high)和低高(low) → 向上合并
- 下降趋势中：取高低(high)和低低(low) → 向下合并
- 顺序处理，从左到右依次合并

输入: [K1, K2, K3, ..., Kn]
输出: [K'1, K'2, ..., K'm]   (m ≤ n, 无包含关系)
```

#### (2) 顶底分型识别

```
顶分型：中间K线高点最高，低点最高（三根K线中的局部高点）
底分型：中间K线低点最低，高点最低（三根K线中的局部低点）

验证规则：
- 顶分型后必须跟底分型（间隔至少1根K线）
- 顶分型最高点 > 相邻底分型最高点
- 底分型最低点 < 相邻顶分型最低点
```

#### (3) 笔的划分

```
笔 = 连接相邻的顶分型和底分型

确认条件：
1. 顶底之间至少包含5根独立K线（含包含处理后）
2. 笔的端点必须是分型
3. 相邻两笔不能同向（必须是顶→底→顶→底交替）

特殊处理：
- 新笔形成破坏旧笔时，以新笔为准
- 笔的延伸：当价格突破前一顶/底时，笔继续延伸
```

#### (4) 线段构建

```
线段 = 至少3笔组成，且有重叠区间

线段终结判断：
1. 特征序列：取线段中间向的笔
2. 特征序列缺口：相邻特征序列之间是否存在价格缺口
3. 无缺口时：特征序列的顶底分型确认线段终结
4. 有缺口时：需要反向线段回补缺口确认

简化实现：
- 取最近N笔的方向序列
- 若连续3笔反向且有重叠 → 新线段形成
```

#### (5) 中枢识别

```
中枢 = 连续三段次级别走势类型的重叠部分

计算方式：
ZG (中枢高点) = min(三段走势的高点)
ZD (中枢低点) = max(三段走势的低点)

中枢区间 = [ZD, ZG]

中枢级别：
- 由构成中枢的走势级别决定
- 本级别中枢 = 次级别三段重叠
- 常见：1分钟/5分钟/30分钟/日线级别中枢
```

#### (6) 买卖点判定

```
第一类买点：下跌趋势完成，出现底背驰
  条件：价格新低 + MACD不新低（或绿柱面积缩小）

第二类买点：第一类买点后回抽不破新低
  条件：次级别回抽结束 + 价格站稳中枢上方

第三类买点：向上离开中枢后回抽不破中枢ZG
  条件：次级别回抽结束 + 不进入中枢区间

卖点：三类卖点为买点的反向对称操作
```

### 1.3 实现复杂度

| 步骤 | 难度 | 关键挑战 |
|------|------|---------|
| 包含处理 | ⭐ | 方向判断 |
| 分型识别 | ⭐⭐ | 局部极值边界情况 |
| 笔的划分 | ⭐⭐⭐ | 新旧笔交替处理 |
| 线段构建 | ⭐⭐⭐⭐ | 特征序列逻辑 |
| 中枢识别 | ⭐⭐⭐ | 级别递归 |
| 买卖点 | ⭐⭐⭐⭐⭐ | 背驰判断主观性 |

---

## 2. 回测引擎 (Backtest Engine)

### 2.1 向量化回测算方法 (主力引擎)

```
核心思路：用 NumPy 向量操作替代 Python for 循环

传统事件驱动（慢）:
for bar in data:          ← Python循环，5000次
    signal = strategy(bar)
    if signal == BUY:
        execute_trade()

向量化回测（快）:
signals = strategy_vectorized(data)    ← 一次NumPy调用计算所有信号
positions = signals.cumsum()           ← 向量化持仓
returns = positions.shift(1) * data['ret']  ← 向量化收益
equity = (1 + returns).cumprod()       ← 向量化资金曲线

性能对比:
- 单只股票5000根K线: 事件驱动 ~2s → 向量化 ~0.02s (100x)
- 300只股票批量: 向量化 + 多进程 ≈ 2-3分钟
```

### 2.2 绩效指标公式

```python
# 核心绩效指标

# 夏普比率 (Sharpe Ratio)
daily_returns = equity_curve.pct_change()
sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std()

# 胜率 (Win Rate)
win_rate = (returns > 0).sum() / (returns != 0).sum()

# 最大回撤 (Max Drawdown)
cummax = equity_curve.cummax()
drawdown = (equity_curve - cummax) / cummax
max_drawdown = drawdown.min()

# 年化收益率 (Annual Return)
total_return = equity_curve[-1] / equity_curve[0] - 1
years = len(data) / 252
annual_return = (1 + total_return) ** (1 / years) - 1

# 盈亏比 (Profit/Loss Ratio)
avg_win = returns[returns > 0].mean()
avg_loss = abs(returns[returns < 0].mean())
profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')

# 卡尔玛比率 (Calmar Ratio)
calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else float('inf')

# 信息比率 (Information Ratio)
excess = daily_returns - benchmark_returns
ir = np.sqrt(252) * excess.mean() / excess.std()
```

### 2.3 批量回测并行策略

```python
# 300只股票并行回测
from multiprocessing import Pool
import numba

@numba.jit(nopython=True)
def _backtest_core(ohlcv, signals, params):
    """Numba加速的回测核心计算"""
    # JIT编译后速度接近C语言
    ...

def backtest_single(args):
    symbol, strategy, params = args
    data = load_parquet(symbol)      # 只读取需要的数据
    signals = strategy.generate(data) # 向量化信号生成
    return _backtest_core(data, signals, params)

# 多进程并行
with Pool(processes=cpu_count()) as pool:
    results = pool.map(backtest_single, tasks)
```

---

## 3. 预测算法

### 3.1 选股预测模型

#### 多因子打分模型 (主力)

```
因子池 (可配置):
├── 估值因子: PE, PB, PS, PEG
├── 盈利因子: ROE, ROA, 毛利率, 净利率
├── 成长因子: 营收增速, 利润增速, EPS增速
├── 动量因子: 1月/3月/6月/12月 收益率
├── 波动因子: 波动率, Beta, 下行标准差
├── 技术因子: RSI位置, MACD信号, 均线位置
├── 质量因子: 资产负债率, 现金流比率, 股息率
└── 情绪因子: 换手率, 成交量变化, 资金流向

打分方法:
1. 等权打分: score = Σ(因子排名百分位 × 1/N)
2. IC加权: 按各因子历史IC值加权
3. 动态权重: 根据近期因子表现自适应调整

输出: 每只股票 0-100 综合评分
```

#### XGBoost 排序模型 (增强)

```python
# 用于股票排序的Learning to Rank
import xgboost as xgb

# 特征: 所有因子值
# 标签: 未来N日收益率排名
# 输出: 股票排序分数

model = xgb.XGBRanker(
    objective='rank:pairwise',
    n_estimators=100,
    max_depth=5
)
model.fit(X_train, y_train, group=group_train)
```

#### LSTM 价格预测 (辅助参考)

```python
# 用于辅助判断趋势方向
# 输入: 过去60天 OHLCV + 技术指标
# 输出: 未来5天涨跌概率

# 注意: 仅作辅助参考信号，不单独决策
```

### 3.2 大盘择时模型

#### 多指标融合模型

```
信号源 (独立计算，投票融合):

1. 均线趋势: MA5/MA20/MA60 多头排列 → 看多 +1
2. MACD: DIF上穿DEA → 看多 +1
3. 布林带: 价格突破上轨 → 看空 -1
4. ADX: ADX>25 + +DI>-DI → 看多 +1
5. RSI: RSI<30 → 超卖反弹 +1, RSI>70 → 超买回落 -1
6. 成交量: 放量上涨 → 看多 +2, 缩量下跌 → 中性 0
7. 市场宽度: 涨跌比>2 → 看多 +1

最终信号 = Σ各信号源分数
  总分 > 2  → BUY
  总分 -2~2 → HOLD
  总分 < -2 → SELL
```

### 3.3 动能评分模型

```
价格动能 (权重 60%):
  - 1月动量 (20%): (当前价/1月前价 - 1) × 排名百分比
  - 3月动量 (20%): (当前价/3月前价 - 1) × 排名百分比
  - RSI强度 (20%): RSI/100 × 20

量能动能 (权重 30%):
  - 量比 (15%): 近5日均量/近20日均量
  - OBV趋势 (15%): OBV斜率方向

资金动能 (权重 10%):
  - 近5日主力净流入率

综合评分 = 价格动能 × 0.6 + 量能动能 × 0.3 + 资金动能 × 0.1
分数范围: 0-100, 分数越高动能越强
```

---

## 4. 算法部署架构

```
┌─────────────────────────────────────────────────┐
│              Python Core Engines                  │
│                                                   │
│  缠论引擎        回测引擎        预测模型          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │纯算法    │  │NumPy+Numba│  │scikit-learn  │   │
│  │无依赖    │  │向量化加速  │  │XGBoost       │   │
│  │          │  │多进程并行  │  │PyTorch(LSTM) │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│                                                   │
│  选股引擎        择时引擎        动能引擎          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │多因子打分 │  │多指标融合  │  │加权评分      │   │
│  │XGBoost排序│  │投票机制    │  │排名百分位    │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## 5. 算法验证标准

| 算法模块 | 验证方法 | 通过标准 |
|---------|---------|---------|
| 缠论分型 | 对比人工标注 100 个案例 | 准确率 > 95% |
| 缠论买卖点 | 对比经典缠论教材图例 | 标注位置一致 |
| 回测引擎 | 对比 backtrader/zipline 结果 | 收益率误差 < 1% |
| 选股打分 | 回测Top-N组合收益 vs 等权组合 | 有显著超额收益 |
| 择时信号 | 对比买入持有策略 | Sharpe提升 > 0.3 |
| 动能评分 | 高分组合 vs 低分组合收益差 | 有显著单调性 |
