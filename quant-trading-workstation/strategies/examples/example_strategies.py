"""
示例策略模板 — 供用户参考和学习
"""

# ============================================================
# 示例1: 双均线交叉策略
# ============================================================
def ma_cross_strategy(data, fast_period=5, slow_period=20):
    """
    经典双均线交叉策略
    - 快线上穿慢线 → 买入
    - 快线下穿慢线 → 卖出
    """
    close = data['close']
    fast_ma = close.rolling(fast_period).mean()
    slow_ma = close.rolling(slow_period).mean()

    # 信号：快线上穿慢线 = 1，下穿 = -1
    signals = (fast_ma > slow_ma).astype(int).diff().clip(-1, 1)
    return signals


# ============================================================
# 示例2: 缠论买卖点策略
# ============================================================
def chan_theory_strategy(data, chan_engine):
    """
    基于缠论买卖点的交易策略
    - 第一/二/三类买点 → 买入
    - 第一/二/三类卖点 → 卖出
    """
    # 使用缠论引擎分析
    analysis = chan_engine.analyze(data)

    signals = pd.Series(0, index=data.index)

    for point in analysis['buy_points']:
        signals.loc[point['date']] = 1

    for point in analysis['sell_points']:
        signals.loc[point['date']] = -1

    return signals


# ============================================================
# 示例3: 动量突破策略
# ============================================================
def momentum_breakout_strategy(data, lookback=20, atr_period=14):
    """
    动量突破策略
    - 价格突破N日高点 → 买入
    - 价格跌破N日低点 → 卖出
    - 使用ATR设置止损
    """
    high = data['high']
    low = data['low']
    close = data['close']

    # 计算通道
    upper = high.rolling(lookback).max()
    lower = low.rolling(lookback).min()

    # 信号
    signals = pd.Series(0, index=data.index)
    signals[close > upper.shift(1)] = 1
    signals[close < lower.shift(1)] = -1

    return signals
