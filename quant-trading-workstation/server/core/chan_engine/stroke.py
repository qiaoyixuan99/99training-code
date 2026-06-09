"""
缠论引擎 — 笔的划分模块
连接相邻顶底分型，构建有效的笔（上升笔/下降笔）
"""
import numpy as np
from typing import List, Optional
from dataclasses import dataclass
from .fractal import Fractal


@dataclass
class Stroke:
    """笔的数据结构"""
    start_index: int       # 起始分型在原始K线中的索引
    end_index: int         # 结束分型在原始K线中的索引
    direction: str         # 'up' | 'down'
    start_price: float     # 起始价格（分型极值）
    end_price: float       # 结束价格（分型极值）
    start_date: any        # 起始日期
    end_date: any          # 结束日期
    high: float            # 笔的最高价
    low: float             # 笔的最低价
    kline_count: int       # 包含K线数量
    strength: float = 0.0  # 笔的力度（价格变动幅度）


def build_strokes(fractals: List[Fractal], df_original, min_kline_count: int = 5) -> List[Stroke]:
    """
    基于分型列表构建笔

    规则：
    1. 相邻分型必须顶底交替（顶→底→顶→底）
    2. 分型之间至少间隔 min_kline_count 根独立K线（不含包含处理）
    3. 上升笔的终点必须高于起点，下降笔的终点必须低于起点

    Args:
        fractals: 已验证交替的分型列表
        df_original: 原始K线DataFrame（未经包含处理，用于计算K线数）
        min_kline_count: 笔的最小K线数，默认5

    Returns:
        笔的列表
    """
    if len(fractals) < 2:
        return []

    strokes = []
    i = 0

    while i < len(fractals) - 1:
        start_f = fractals[i]
        end_f = fractals[i + 1]

        # 方向判断：底分型 → 顶分型 = 上升笔，顶分型 → 底分型 = 下降笔
        if start_f.type == 'bottom' and end_f.type == 'top':
            direction = 'up'
            start_price = start_f.low
            end_price = end_f.high
        elif start_f.type == 'top' and end_f.type == 'bottom':
            direction = 'down'
            start_price = start_f.high
            end_price = end_f.low
        else:
            # 同类型分型，跳过
            i += 1
            continue

        # 合法性检查
        if direction == 'up' and end_price <= start_price:
            i += 1
            continue
        if direction == 'down' and end_price >= start_price:
            i += 1
            continue

        # 计算K线数量
        kline_count = end_f.index - start_f.index + 1

        if kline_count < min_kline_count:
            i += 1
            continue

        # 计算笔的最高/最低价
        segment_df = df_original.iloc[start_f.index:end_f.index + 1]
        stroke_high = segment_df['high'].max()
        stroke_low = segment_df['low'].min()

        # 计算力度
        strength = abs(end_price - start_price) / start_price if start_price > 0 else 0

        stroke = Stroke(
            start_index=start_f.index,
            end_index=end_f.index,
            direction=direction,
            start_price=start_price,
            end_price=end_price,
            start_date=start_f.date,
            end_date=end_f.date,
            high=stroke_high,
            low=stroke_low,
            kline_count=kline_count,
            strength=round(strength * 100, 4),  # 百分比
        )
        strokes.append(stroke)
        i += 1

    return strokes


def validate_stroke_alternation(strokes: List[Stroke]) -> List[Stroke]:
    """
    确保笔的方向严格交替（上升→下降→上升→下降）
    处理包含关系的笔
    """
    if len(strokes) < 2:
        return strokes

    valid = [strokes[0]]
    for s in strokes[1:]:
        prev = valid[-1]
        # 方向必须交替
        if s.direction == prev.direction:
            # 同方向笔，取延伸（更强的那个）
            if s.direction == 'up' and s.end_price > prev.end_price:
                # 新笔延伸更长，替换
                combined = Stroke(
                    start_index=prev.start_index,
                    end_index=s.end_index,
                    direction='up',
                    start_price=prev.start_price,
                    end_price=s.end_price,
                    start_date=prev.start_date,
                    end_date=s.end_date,
                    high=max(prev.high, s.high),
                    low=min(prev.low, s.low),
                    kline_count=prev.kline_count + s.kline_count,
                    strength=round(abs(s.end_price - prev.start_price) / prev.start_price * 100, 4),
                )
                valid[-1] = combined
            elif s.direction == 'down' and s.end_price < prev.end_price:
                combined = Stroke(
                    start_index=prev.start_index,
                    end_index=s.end_index,
                    direction='down',
                    start_price=prev.start_price,
                    end_price=s.end_price,
                    start_date=prev.start_date,
                    end_date=s.end_date,
                    high=max(prev.high, s.high),
                    low=min(prev.low, s.low),
                    kline_count=prev.kline_count + s.kline_count,
                    strength=round(abs(prev.start_price - s.end_price) / prev.start_price * 100, 4),
                )
                valid[-1] = combined
            # 否则保留原笔，跳过新笔
        else:
            valid.append(s)

    return valid
