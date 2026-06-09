"""技术指标计算 — 纯函数，输入K线列表，输出指标结果"""

from typing import List, Dict, Any, Optional
from .data import KlineBar


def _closes(klines: List[KlineBar]) -> List[float]:
    return [k.close for k in klines]


def _highs(klines: List[KlineBar]) -> List[float]:
    return [k.high for k in klines]


def _lows(klines: List[KlineBar]) -> List[float]:
    return [k.low for k in klines]


def _volumes(klines: List[KlineBar]) -> List[float]:
    return [k.volume for k in klines]


def _sma(values: List[float], period: int) -> List[Optional[float]]:
    """简单移动平均，不足period的位置返回None"""
    result = [None] * len(values)
    if len(values) < period:
        return result
    window_sum = sum(values[:period])
    result[period - 1] = window_sum / period
    for i in range(period, len(values)):
        window_sum += values[i] - values[i - period]
        result[i] = window_sum / period
    return result


def _ema(values: List[float], period: int) -> List[Optional[float]]:
    """指数移动平均"""
    result = [None] * len(values)
    if len(values) < period:
        return result
    # 初始值用SMA
    result[period - 1] = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    for i in range(period, len(values)):
        result[i] = (values[i] - result[i - 1]) * multiplier + result[i - 1]
    return result


def ma(klines: List[KlineBar], period: int) -> List[Optional[float]]:
    """移动平均线 (SMA)"""
    return _sma(_closes(klines), period)


def ema(klines: List[KlineBar], period: int) -> List[Optional[float]]:
    """指数移动平均线"""
    return _ema(_closes(klines), period)


# ---- MACD ----

def macd(klines: List[KlineBar], fast: int = 12, slow: int = 26, signal: int = 9
         ) -> Dict[str, List[Optional[float]]]:
    """MACD指标

    Returns:
        {'dif': [...], 'dea': [...], 'histogram': [...]}  (histogram = 2*(DIF-DEA))
    """
    closes = _closes(klines)
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)

    dif = [None] * len(closes)
    for i in range(len(closes)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            dif[i] = ema_fast[i] - ema_slow[i]

    # DEA = EMA of DIF
    dea = [None] * len(closes)
    valid_dif = [(i, v) for i, v in enumerate(dif) if v is not None]
    if len(valid_dif) >= signal:
        dea_vals = [v for _, v in valid_dif]
        dea_ema = _ema_from_list(dea_vals, signal)
        for j, (idx, _) in enumerate(valid_dif):
            dea[idx] = dea_ema[j]

    histogram = [None] * len(closes)
    for i in range(len(closes)):
        if dif[i] is not None and dea[i] is not None:
            histogram[i] = 2 * (dif[i] - dea[i])

    return {'dif': dif, 'dea': dea, 'histogram': histogram}


def _ema_from_list(values: List[float], period: int) -> List[Optional[float]]:
    """对任意序列计算EMA"""
    result = [None] * len(values)
    if len(values) < period:
        return result
    result[period - 1] = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    for i in range(period, len(values)):
        result[i] = (values[i] - result[i - 1]) * multiplier + result[i - 1]
    return result


# ---- RSI ----

def rsi(klines: List[KlineBar], period: int = 14) -> List[Optional[float]]:
    """RSI 相对强弱指标"""
    closes = _closes(klines)
    result = [None] * len(closes)

    if len(closes) < period + 1:
        return result

    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    idx = period  # closes index (0-based)
    if avg_loss == 0:
        result[idx] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[idx] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period, len(gains)):
        idx = i + 1
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[idx] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[idx] = 100.0 - (100.0 / (1.0 + rs))

    return result


# ---- 布林带 ----

def bollinger(klines: List[KlineBar], period: int = 20, std_mult: float = 2.0
              ) -> Dict[str, List[Optional[float]]]:
    """布林带

    Returns:
        {'upper': [...], 'middle': [...], 'lower': [...]}
    """
    closes = _closes(klines)
    middle = _sma(closes, period)

    upper = [None] * len(closes)
    lower = [None] * len(closes)

    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1: i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance ** 0.5
        upper[i] = mean + std_mult * std
        lower[i] = mean - std_mult * std

    return {'upper': upper, 'middle': middle, 'lower': lower}


# ---- KDJ ----

def kdj(klines: List[KlineBar], period: int = 9, k_period: int = 3, d_period: int = 3
        ) -> Dict[str, List[Optional[float]]]:
    """KDJ 随机指标

    Returns:
        {'k': [...], 'd': [...], 'j': [...]}
    """
    highs = _highs(klines)
    lows = _lows(klines)
    closes = _closes(klines)
    n = len(klines)

    rsv = [None] * n
    for i in range(period - 1, n):
        h = max(highs[i - period + 1: i + 1])
        l = min(lows[i - period + 1: i + 1])
        rsv[i] = ((closes[i] - l) / (h - l) * 100) if h != l else 50.0

    k = [None] * n
    d = [None] * n
    j = [None] * n

    for i in range(n):
        if rsv[i] is None:
            continue
        if i == 0 or k[i - 1] is None:
            k[i] = 50.0
            d[i] = 50.0
        else:
            k[i] = (k_period - 1) / k_period * k[i - 1] + (1 / k_period) * rsv[i]
            d[i] = (d_period - 1) / d_period * d[i - 1] + (1 / d_period) * k[i]
        j[i] = 3 * k[i] - 2 * d[i]

    return {'k': k, 'd': d, 'j': j}


# ---- ATR ----

def atr(klines: List[KlineBar], period: int = 14) -> List[Optional[float]]:
    """ATR 平均真实波幅"""
    n = len(klines)
    result = [None] * n

    if n < 2:
        return result

    tr_values = [None] * n
    tr_values[0] = klines[0].high - klines[0].low
    for i in range(1, n):
        high_low = klines[i].high - klines[i].low
        high_prev = abs(klines[i].high - klines[i - 1].close)
        low_prev = abs(klines[i].low - klines[i - 1].close)
        tr_values[i] = max(high_low, high_prev, low_prev)

    # 初始ATR用简单平均
    if n >= period:
        result[period - 1] = sum(tr_values[:period]) / period
        for i in range(period, n):
            result[i] = (result[i - 1] * (period - 1) + tr_values[i]) / period

    return result


# ---- 量价分析 ----

def volume_profile(klines: List[KlineBar], bins: int = 10
                   ) -> Dict[str, Any]:
    """量价分布分析

    Returns:
        {'poc': float, 'value_area': (low, high), 'volume_ratio': float, 'avg_volume': float}
    """
    if not klines:
        return {'poc': 0, 'value_area': (0, 0), 'volume_ratio': 0, 'avg_volume': 0}

    price_min = min(k.low for k in klines)
    price_max = max(k.high for k in klines)
    price_range = price_max - price_min or 1.0
    bin_size = price_range / bins

    profile = [0.0] * bins
    for k in klines:
        # 将成交量按K线在价格区间的占比分配到各bin
        k_low_pct = (k.low - price_min) / price_range
        k_high_pct = (k.high - price_min) / price_range
        bin_low = max(0, min(bins - 1, int(k_low_pct * bins)))
        bin_high = max(0, min(bins - 1, int(k_high_pct * bins)))
        if bin_low == bin_high:
            profile[bin_low] += k.volume
        else:
            vol_per_bin = k.volume / (bin_high - bin_low + 1)
            for b in range(bin_low, bin_high + 1):
                profile[b] += vol_per_bin

    # POC = 成交量最大的价格
    max_bin = profile.index(max(profile))
    poc = price_min + (max_bin + 0.5) * bin_size

    # 70%价值区域
    total_vol = sum(profile)
    target = total_vol * 0.7
    sorted_bins = sorted(enumerate(profile), key=lambda x: x[1], reverse=True)
    accumulated = 0
    selected = []
    for idx, vol in sorted_bins:
        accumulated += vol
        selected.append(idx)
        if accumulated >= target:
            break
    va_low = price_min + min(selected) * bin_size
    va_high = price_min + (max(selected) + 1) * bin_size

    avg_vol = sum(k.volume for k in klines) / len(klines)
    latest_vol = klines[-1].volume
    vol_ratio = latest_vol / avg_vol if avg_vol > 0 else 1.0

    return {
        'poc': round(poc, 2),
        'value_area': (round(va_low, 2), round(va_high, 2)),
        'volume_ratio': round(vol_ratio, 2),
        'avg_volume': round(avg_vol, 0),
    }


# ---- 聚合计算 ----

def _last(series: List[Optional[float]]) -> Optional[float]:
    """取序列最后一个有效值"""
    for v in reversed(series):
        if v is not None:
            return round(v, 4)
    return None


def _last_dict(d: Dict[str, List[Optional[float]]]) -> Dict[str, Optional[float]]:
    return {k: _last(v) for k, v in d.items()}


def compute_all_indicators(klines: List[KlineBar]) -> Dict[str, Any]:
    """一次性计算所有技术指标，返回结构化字典

    返回格式适合直接序列化为JSON，便于传递给Strategy/Predictor接口。
    """
    atr_last = _last(atr(klines))
    return {
        'ma': {
            'ma5': _last(ma(klines, 5)),
            'ma10': _last(ma(klines, 10)),
            'ma20': _last(ma(klines, 20)),
            'ma60': _last(ma(klines, 60)),
        },
        'macd': _last_dict(macd(klines)),
        'rsi': {
            'rsi6': _last(rsi(klines, 6)),
            'rsi14': _last(rsi(klines, 14)),
            'rsi24': _last(rsi(klines, 24)),
        },
        'bollinger': _last_dict(bollinger(klines)),
        'kdj': _last_dict(kdj(klines)),
        'atr': atr_last,
        'atr_pct': round(atr_last / klines[-1].close * 100, 2) if atr_last and klines else None,
        'volume': volume_profile(klines),
    }
