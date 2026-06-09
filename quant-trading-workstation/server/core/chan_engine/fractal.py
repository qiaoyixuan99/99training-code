"""
缠论引擎 — 顶底分型识别模块
实现K线包含处理、顶底分型检测
"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Fractal:
    """分型数据结构"""
    index: int           # K线索引位置
    type: str            # 'top' | 'bottom'
    high: float
    low: float
    date: any


def process_containment(df: pd.DataFrame) -> pd.DataFrame:
    """
    K线包含处理（标准化）

    规则：
    - 上升趋势中(前一根K线收阳)：取高高+低高 → 向上合并
    - 下降趋势中(前一根K线收阴)：取高低+低低 → 向下合并

    Args:
        df: 原始K线 DataFrame [open, high, low, close]

    Returns:
        处理后的 DataFrame，包含关系K线被合并
    """
    if len(df) < 2:
        return df.copy()

    result = []
    i = 0

    while i < len(df):
        current = df.iloc[i]
        # 统一转为 dict
        cur_dict = {
            'open': float(current['open']),
            'high': float(current['high']),
            'low': float(current['low']),
            'close': float(current['close']),
        }

        if i == 0:
            result.append(cur_dict)
            i += 1
            continue

        prev = result[-1]
        prev_direction = 'up' if prev['close'] >= prev['open'] else 'down'

        # 判断包含关系
        if _has_containment(prev, cur_dict):
            # 合并
            if prev_direction == 'up':
                merged_high = max(prev['high'], cur_dict['high'])
                merged_low = max(prev['low'], cur_dict['low'])
            else:
                merged_high = min(prev['high'], cur_dict['high'])
                merged_low = min(prev['low'], cur_dict['low'])

            # 合并方向：新K线close vs open决定阴阳
            merged = {
                'open': prev['open'],
                'high': merged_high,
                'low': merged_low,
                'close': cur_dict['close'],
            }
            result[-1] = merged  # 替换前一根
        else:
            result.append(cur_dict)

        i += 1

    return pd.DataFrame(result)


def detect_fractals(df: pd.DataFrame) -> List[Fractal]:
    """
    识别顶底分型

    顶分型条件：中间K线高点 > 左右K线高点 且 中间K线低点 > 左右K线低点
    底分型条件：中间K线低点 < 左右K线低点 且 中间K线高点 < 左右K线高点

    Args:
        df: 包含处理后的K线 DataFrame

    Returns:
        分型列表
    """
    fractals = []

    for i in range(1, len(df) - 1):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]
        next_ = df.iloc[i + 1]

        # 顶分型
        if (curr['high'] > prev['high'] and curr['high'] > next_['high'] and
                curr['low'] > prev['low'] and curr['low'] > next_['low']):
            fractals.append(Fractal(
                index=i,
                type='top',
                high=curr['high'],
                low=curr['low'],
                date=df.index[i],
            ))

        # 底分型
        if (curr['low'] < prev['low'] and curr['low'] < next_['low'] and
                curr['high'] < prev['high'] and curr['high'] < next_['high']):
            fractals.append(Fractal(
                index=i,
                type='bottom',
                high=curr['high'],
                low=curr['low'],
                date=df.index[i],
            ))

    # 确保顶底交替（保留第一个分型，后续交替验证）
    return _validate_alternation(fractals)


def _has_containment(k1, k2) -> bool:
    """判断两根K线是否存在包含关系"""
    return (k1['high'] >= k2['high'] and k1['low'] <= k2['low']) or \
           (k1['high'] <= k2['high'] and k1['low'] >= k2['low'])


def _validate_alternation(fractals: List[Fractal]) -> List[Fractal]:
    """确保分型顶底交替，去除连续同类型分型"""
    if len(fractals) < 2:
        return fractals

    valid = [fractals[0]]
    for f in fractals[1:]:
        if f.type != valid[-1].type:
            # 顶分型的顶 > 前一底分型的顶，底分型的底 < 前一顶分型的底
            if f.type == 'top' and f.high > valid[-1].high:
                valid.append(f)
            elif f.type == 'bottom' and f.low < valid[-1].low:
                valid.append(f)
            # 否则跳过这个分型

    return valid
