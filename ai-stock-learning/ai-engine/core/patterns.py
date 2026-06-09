"""K线形态识别 — 纯函数，输入K线列表，输出形态检测结果"""

from typing import List, Dict, Any, Optional, Tuple
from .data import KlineBar


def detect_doji(klines: List[KlineBar], body_ratio_threshold: float = 0.1,
                shadow_ratio: float = 2.0) -> List[Dict[str, Any]]:
    """检测十字星形态

    条件：实体占比 < 10% 且 影线长度 > 实体*2
    """
    results = []
    for i, k in enumerate(klines):
        if k.body_ratio > body_ratio_threshold:
            continue
        if k.upper_shadow + k.lower_shadow < k.body * shadow_ratio:
            continue

        # 分类
        if k.upper_shadow > k.lower_shadow * 1.5:
            doji_type = '墓碑十字'  # 上影线长 → 看跌
        elif k.lower_shadow > k.upper_shadow * 1.5:
            doji_type = '蜻蜓十字'  # 下影线长 → 看涨
        else:
            doji_type = '标准十字星'

        # 位置判断
        position = _price_position(k, klines, i)

        results.append({
            'index': i,
            'time': k.time,
            'type': 'doji',
            'doji_type': doji_type,
            'position': position,
            'signal': 'reversal',  # 十字星本质是反转信号
            'strength': 3 if position in ('高位', '低位') else 1,
        })
    return results


def detect_hammer(klines: List[KlineBar], body_ratio_max: float = 0.3,
                  lower_shadow_min: float = 2.0) -> List[Dict[str, Any]]:
    """检测锤子线 / 倒锤子 / 上吊线

    锤子（看涨）：下影线 >= 实体*2，实体小，位于下跌趋势末端
    倒锤子（看涨）：上影线 >= 实体*2，实体小，位于下跌趋势末端
    上吊线（看跌）：下影线 >= 实体*2，实体小，位于上涨趋势末端
    """
    results = []
    for i, k in enumerate(klines):
        if k.body == 0:
            continue

        lower_ratio = k.lower_shadow / k.body
        upper_ratio = k.upper_shadow / k.body
        position = _price_position(k, klines, i)
        short_term_trend = _local_trend(klines, i, 5)

        # 锤子线 / 上吊线（长下影）
        if lower_ratio >= lower_shadow_min and upper_ratio < 1:
            if short_term_trend == 'down' and position == '低位':
                results.append({
                    'index': i, 'time': k.time, 'type': 'hammer',
                    'name': '锤子线', 'signal': 'bullish',
                    'strength': 6 if k.volume > _avg_volume(klines, i, 20) else 4,
                })
            elif short_term_trend == 'up' and position == '高位':
                results.append({
                    'index': i, 'time': k.time, 'type': 'hanging_man',
                    'name': '上吊线', 'signal': 'bearish',
                    'strength': 5 if k.volume > _avg_volume(klines, i, 20) else 3,
                })

        # 倒锤子（长上影）
        elif upper_ratio >= lower_shadow_min and lower_ratio < 1:
            if short_term_trend == 'down' and position == '低位':
                results.append({
                    'index': i, 'time': k.time, 'type': 'inverted_hammer',
                    'name': '倒锤子', 'signal': 'bullish',
                    'strength': 5,
                })
            elif short_term_trend == 'up' and position == '高位':
                results.append({
                    'index': i, 'time': k.time, 'type': 'shooting_star',
                    'name': '射击之星', 'signal': 'bearish',
                    'strength': 6 if k.volume > _avg_volume(klines, i, 20) else 4,
                })

    return results


def detect_engulfing(klines: List[KlineBar]) -> List[Dict[str, Any]]:
    """检测吞没形态

    看涨吞没：前阴后阳，后阳实体完全包住前阴实体
    看跌吞没：前阳后阴，后阴实体完全包住前阳实体
    """
    results = []
    for i in range(1, len(klines)):
        prev = klines[i - 1]
        curr = klines[i]

        # 看涨吞没：前一根阴线，当前阳线，实体完全覆盖
        if (not prev.is_up and curr.is_up
                and curr.open <= prev.close
                and curr.close >= prev.open
                and curr.body > prev.body):
            results.append({
                'index': i, 'time': curr.time, 'type': 'bullish_engulfing',
                'name': '看涨吞没', 'signal': 'bullish',
                'strength': 7 if curr.volume > _avg_volume(klines, i, 20) else 5,
            })

        # 看跌吞没：前一根阳线，当前阴线，实体完全覆盖
        if (prev.is_up and not curr.is_up
                and curr.open >= prev.close
                and curr.close <= prev.open
                and curr.body > prev.body):
            results.append({
                'index': i, 'time': curr.time, 'type': 'bearish_engulfing',
                'name': '看跌吞没', 'signal': 'bearish',
                'strength': 7 if curr.volume > _avg_volume(klines, i, 20) else 5,
            })

    return results


def detect_support_resistance(klines: List[KlineBar],
                              lookback: int = 50,
                              tolerance: float = 0.02
                              ) -> Dict[str, List[float]]:
    """检测支撑/压力位（基于局部极值聚类）

    Returns:
        {'support': [prices...], 'resistance': [prices...],
         'nearest_support': float|None, 'nearest_resistance': float|None}
    """
    n = len(klines)
    if n < lookback:
        lookback = max(n // 2, 5)

    peaks = []
    valleys = []

    # 局部极值扫描
    window = max(3, lookback // 5)
    for i in range(window, n - window):
        left = klines[i - window: i]
        right = klines[i + 1: i + window + 1]
        curr = klines[i]

        if all(k.high <= curr.high for k in left) and all(k.high <= curr.high for k in right):
            peaks.append(curr.high)
        if all(k.low >= curr.low for k in left) and all(k.low >= curr.low for k in right):
            valleys.append(curr.low)

    # 价格聚类
    support = _cluster_prices(valleys, tolerance)
    resistance = _cluster_prices(peaks, tolerance)

    latest_close = klines[-1].close
    nearest_support = _nearest_level(support, latest_close, 'below')
    nearest_resistance = _nearest_level(resistance, latest_close, 'above')

    return {
        'support': [round(s, 2) for s in support],
        'resistance': [round(r, 2) for r in resistance],
        'nearest_support': round(nearest_support, 2) if nearest_support else None,
        'nearest_resistance': round(nearest_resistance, 2) if nearest_resistance else None,
    }


def detect_trend(klines: List[KlineBar], short_period: int = 20,
                 long_period: int = 60) -> Dict[str, Any]:
    """判断当前趋势（上涨/下跌/横盘）

    综合短期均线排列、中长期均线方向、价格位置来判断
    """
    n = len(klines)
    if n < long_period:
        short_period = min(10, n // 2)
        long_period = min(30, n - 1)

    closes = [k.close for k in klines]

    # 均线计算
    ma5 = _calc_ma(closes, min(5, n))
    ma10 = _calc_ma(closes, min(10, n))
    ma20 = _calc_ma(closes, min(short_period, n))
    ma60 = _calc_ma(closes, min(long_period, n))

    latest = closes[-1]

    # 短期趋势：MA5 vs MA10 vs MA20 排列
    if ma5[-1] is not None and ma10[-1] is not None and ma20[-1] is not None:
        if ma5[-1] > ma10[-1] > ma20[-1]:
            short_trend = 'up'
        elif ma5[-1] < ma10[-1] < ma20[-1]:
            short_trend = 'down'
        else:
            short_trend = 'sideways'
    else:
        short_trend = 'uncertain'

    # 中长期趋势：MA20方向 + 价格相对MA60位置
    if ma20[-1] is not None and ma20[-5] is not None:
        ma20_slope = (ma20[-1] - ma20[-5]) / abs(ma20[-5]) * 100 if ma20[-5] else 0
    else:
        ma20_slope = 0

    if ma60[-1] is not None:
        price_vs_ma60 = (latest - ma60[-1]) / ma60[-1] * 100
    else:
        price_vs_ma60 = 0

    # 综合判断
    if short_trend == 'up' and ma20_slope > 0 and price_vs_ma60 > 0:
        overall_trend = '强势上涨'
        trend_score = 80
    elif short_trend == 'up':
        overall_trend = '短期反弹'
        trend_score = 60
    elif short_trend == 'down' and ma20_slope < 0 and price_vs_ma60 < 0:
        overall_trend = '弱势下跌'
        trend_score = 20
    elif short_trend == 'down':
        overall_trend = '短期回调'
        trend_score = 40
    elif ma20_slope > 0 and price_vs_ma60 > 0:
        overall_trend = '震荡偏多'
        trend_score = 55
    elif ma20_slope < 0 and price_vs_ma60 < 0:
        overall_trend = '震荡偏空'
        trend_score = 45
    else:
        overall_trend = '横盘整理'
        trend_score = 50

    return {
        'overall': overall_trend,
        'score': trend_score,
        'short_term': short_trend,
        'ma20_direction': 'up' if ma20_slope > 0.5 else 'down' if ma20_slope < -0.5 else 'flat',
        'price_vs_ma60_pct': round(price_vs_ma60, 2),
        'ma5': round(ma5[-1], 2) if ma5[-1] else None,
        'ma10': round(ma10[-1], 2) if ma10[-1] else None,
        'ma20': round(ma20[-1], 2) if ma20[-1] else None,
        'ma60': round(ma60[-1], 2) if ma60[-1] else None,
    }


# ---- 聚合检测 ----

def detect_all_patterns(klines: List[KlineBar]) -> Dict[str, Any]:
    """一次性运行所有形态检测，返回结构化结果"""
    return {
        'doji': detect_doji(klines),
        'hammer': detect_hammer(klines),
        'engulfing': detect_engulfing(klines),
        'levels': detect_support_resistance(klines),
        'trend': detect_trend(klines),
        # 最近出现的信号汇总
        'latest_signals': _summarize_latest(klines),
    }


# ---- 内部辅助函数 ----

def _price_position(k: KlineBar, klines: List[KlineBar], idx: int,
                    lookback: int = 20) -> str:
    """判断当前K线在近期价格中的位置（高位/中位/低位）"""
    start = max(0, idx - lookback)
    end = min(len(klines), idx + lookback + 1)
    window = klines[start:end]
    if not window:
        return '中位'
    high_max = max(b.high for b in window)
    low_min = min(b.low for b in window)
    price_range = high_max - low_min or 1
    pos_pct = (k.close - low_min) / price_range
    if pos_pct > 0.7:
        return '高位'
    elif pos_pct < 0.3:
        return '低位'
    return '中位'


def _local_trend(klines: List[KlineBar], idx: int, lookback: int = 5) -> str:
    """局部趋势判断"""
    if idx < lookback:
        return 'uncertain'
    closes = [klines[i].close for i in range(idx - lookback, idx + 1)]
    first = closes[0]
    last = closes[-1]
    change_pct = (last - first) / first * 100 if first != 0 else 0
    if change_pct > 2:
        return 'up'
    elif change_pct < -2:
        return 'down'
    return 'flat'


def _avg_volume(klines: List[KlineBar], idx: int, lookback: int = 20) -> float:
    """局部平均成交量"""
    start = max(0, idx - lookback)
    window = klines[start:idx + 1]
    return sum(k.volume for k in window) / len(window) if window else 0


def _calc_ma(values: List[float], period: int) -> List[Optional[float]]:
    """简单移动平均"""
    result: List[Optional[float]] = [None] * len(values)
    if len(values) < period:
        return result
    window_sum = sum(values[:period])
    result[period - 1] = window_sum / period
    for i in range(period, len(values)):
        window_sum += values[i] - values[i - period]
        result[i] = window_sum / period
    return result


def _cluster_prices(prices: List[float], tolerance: float) -> List[float]:
    """价格聚类：将相近价格合并"""
    if not prices:
        return []
    sorted_p = sorted(prices)
    clusters = []
    current = [sorted_p[0]]
    for p in sorted_p[1:]:
        avg = sum(current) / len(current)
        if abs(p - avg) / avg < tolerance:
            current.append(p)
        else:
            clusters.append(sum(current) / len(current))
            current = [p]
    clusters.append(sum(current) / len(current))
    return sorted(set(round(c, 2) for c in clusters))


def _nearest_level(levels: List[float], price: float, direction: str) -> Optional[float]:
    """找最近的关键价位"""
    if direction == 'below':
        below = [l for l in levels if l < price]
        return max(below) if below else None
    else:
        above = [l for l in levels if l > price]
        return min(above) if above else None


def _summarize_latest(klines: List[KlineBar]) -> List[Dict[str, Any]]:
    """汇总最近5根K线的形态信号"""
    if len(klines) < 5:
        return []
    recent = klines[-5:]
    signals = []
    for pattern_func in [detect_doji, detect_hammer, detect_engulfing]:
        results = pattern_func(recent)
        for r in results:
            r['time'] = recent[r['index']].time
            signals.append(r)
    return signals
