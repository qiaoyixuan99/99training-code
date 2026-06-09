"""
缠论引擎 — 中枢识别模块
识别走势中的价格中枢（震荡区间），计算中枢级别和引力
"""
import numpy as np
from typing import List, Optional
from dataclasses import dataclass
from .segment import Segment
from .stroke import Stroke


@dataclass
class Center:
    """中枢数据结构"""
    zg: float                # 中枢高点（上轨）
    zd: float                # 中枢低点（下轨）
    zz: float                # 中枢中轴（引力线）
    start_index: int         # 起始K线索引
    end_index: int           # 结束K线索引
    start_date: any
    end_date: any
    segments: List[int]      # 构成中枢的线段索引
    level: str               # 级别 '1m'|'5m'|'15m'|'30m'|'60m'|'1d'
    strength: float = 0.0    # 中枢强度（重叠度）
    kline_count: int = 0     # 覆盖K线数


def build_centers(segments: List[Segment], strokes: List[Stroke],
                  df_original, period: str = '1d') -> List[Center]:
    """
    识别中枢（至少三段次级别走势的重叠区间）

    简化的中枢识别逻辑：
    1. 取连续线段，找重叠区间
    2. 至少3段重叠构成中枢
    3. ZG = min(各线段高点), ZD = max(各线段低点)
    4. ZG > ZD 才构成有效中枢

    Args:
        segments: 线段列表
        strokes: 笔列表（备用，当线段不足时降级用笔构建）
        df_original: 原始K线DataFrame
        period: K线周期，用于确定级别

    Returns:
        中枢列表
    """
    centers = []

    # 优先用线段构建中枢，线段不足时降级用笔
    if len(segments) >= 3:
        centers.extend(_build_centers_from_segments(segments, df_original, period))
    elif len(strokes) >= 3:
        centers.extend(_build_centers_from_strokes(strokes, df_original, period))

    return _merge_overlapping_centers(centers)


def _build_centers_from_segments(
    segments: List[Segment], df_original, period: str
) -> List[Center]:
    """基于线段构建中枢"""
    centers = []
    i = 0

    while i < len(segments) - 2:
        # 取3段连续线段
        seg_triple = segments[i:i + 3]

        # 计算重叠区间
        highs = [s.high for s in seg_triple]
        lows = [s.low for s in seg_triple]

        zg = min(highs)  # 中枢高点 = 各线段高点的最小值
        zd = max(lows)   # 中枢低点 = 各线段低点的最大值

        if zg > zd:
            # 有效中枢（重叠区间为正）
            zz = (zg + zd) / 2  # 中枢中轴

            center = Center(
                zg=round(zg, 2),
                zd=round(zd, 2),
                zz=round(zz, 2),
                start_index=seg_triple[0].start_index,
                end_index=seg_triple[-1].end_index,
                start_date=seg_triple[0].start_date,
                end_date=seg_triple[-1].end_date,
                segments=[i, i + 1, i + 2],
                level=_determine_level(period, 'segment'),
                strength=round((zg - zd) / zz * 100, 2) if zz > 0 else 0,
                kline_count=seg_triple[-1].end_index - seg_triple[0].start_index,
            )
            centers.append(center)

        # 扩展中枢：尝试加入更多线段
        j = i + 3
        extended_highs = list(highs)
        extended_lows = list(lows)

        while j < len(segments):
            extended_highs.append(segments[j].high)
            extended_lows.append(segments[j].low)

            new_zg = min(extended_highs)
            new_zd = max(extended_lows)

            if new_zg > new_zd:
                # 中枢扩展
                centers[-1].zg = round(new_zg, 2)
                centers[-1].zd = round(new_zd, 2)
                centers[-1].zz = round((new_zg + new_zd) / 2, 2)
                centers[-1].end_index = segments[j].end_index
                centers[-1].end_date = segments[j].end_date
                centers[-1].segments.append(j)
                centers[-1].kline_count = segments[j].end_index - centers[-1].start_index
                j += 1
            else:
                break  # 重叠消失，中枢结束

        i = j  # 跳到中枢之后

    return centers


def _build_centers_from_strokes(
    strokes: List[Stroke], df_original, period: str
) -> List[Center]:
    """降级方案：基于笔构建中枢"""
    centers = []
    i = 0

    while i < len(strokes) - 2:
        stroke_triple = strokes[i:i + 3]

        highs = [s.high for s in stroke_triple]
        lows = [s.low for s in stroke_triple]

        zg = min(highs)
        zd = max(lows)

        if zg > zd:
            zz = (zg + zd) / 2
            center = Center(
                zg=round(zg, 2),
                zd=round(zd, 2),
                zz=round(zz, 2),
                start_index=stroke_triple[0].start_index,
                end_index=stroke_triple[-1].end_index,
                start_date=stroke_triple[0].start_date,
                end_date=stroke_triple[-1].end_date,
                segments=[],  # 基于笔的中枢没有segment引用
                level=_determine_level(period, 'stroke'),
                strength=round((zg - zd) / zz * 100, 2) if zz > 0 else 0,
                kline_count=stroke_triple[-1].end_index - stroke_triple[0].start_index,
            )
            centers.append(center)

            # 扩展
            j = i + 3
            ext_highs = list(highs)
            ext_lows = list(lows)
            while j < len(strokes):
                ext_highs.append(strokes[j].high)
                ext_lows.append(strokes[j].low)
                new_zg = min(ext_highs)
                new_zd = max(ext_lows)
                if new_zg > new_zd:
                    centers[-1].zg = round(new_zg, 2)
                    centers[-1].zd = round(new_zd, 2)
                    centers[-1].zz = round((new_zg + new_zd) / 2, 2)
                    centers[-1].end_index = strokes[j].end_index
                    centers[-1].end_date = strokes[j].end_date
                    centers[-1].kline_count = strokes[j].end_index - centers[-1].start_index
                    j += 1
                else:
                    break
        i += 1

    return centers


def _merge_overlapping_centers(centers: List[Center]) -> List[Center]:
    """合并重叠的中枢"""
    if len(centers) < 2:
        return centers

    merged = [centers[0]]
    for c in centers[1:]:
        prev = merged[-1]
        # 检查是否重叠
        if c.start_index <= prev.end_index:
            # 重叠，合并为更大的中枢（取交集？取更宽的区间）
            if c.zg < prev.zg and c.zd > prev.zd:
                # c 的中枢区间被 prev 包含，跳过 c
                continue
            if prev.zg < c.zg and prev.zd > c.zd:
                # prev 被 c 包含，替换
                merged[-1] = c
                continue
            # 部分重叠，扩展
            merged[-1].zg = round(min(prev.zg, c.zg), 2) if prev.zg > c.zd else round(max(prev.zg, c.zg), 2)
            merged[-1].zd = round(max(prev.zd, c.zd), 2) if prev.zd < c.zg else round(min(prev.zd, c.zd), 2)
            merged[-1].zz = round((merged[-1].zg + merged[-1].zd) / 2, 2)
            merged[-1].end_index = max(prev.end_index, c.end_index)
            merged[-1].end_date = c.end_date
            merged[-1].kline_count = merged[-1].end_index - merged[-1].start_index
        else:
            merged.append(c)

    return merged


def _determine_level(period: str, source: str) -> str:
    """根据数据周期确定中枢级别"""
    if source == 'segment':
        # 线段构成的中枢为本级别中枢
        return period
    else:
        # 笔构成的中枢为次级别中枢
        level_map = {
            '60m': '30m', '30m': '15m', '15m': '5m',
            '5m': '1m', '1d': '60m', '1w': '1d', '1M': '1w',
            'daily': '60m', 'weekly': '1d', 'monthly': '1w',
        }
        return level_map.get(period, period)


def analyze_center_gravity(centers: List[Center], current_price: float) -> dict:
    """
    分析中枢引力：当前价格与各中枢的关系

    Returns:
        {
            'nearest_support': float,     # 最近支撑位
            'nearest_resistance': float,  # 最近阻力位
            'position': str,              # 'above_all'|'below_all'|'inside'|'between'
            'centers_above': int,         # 上方中枢数
            'centers_below': int,         # 下方中枢数
        }
    """
    if not centers:
        return {
            'nearest_support': None,
            'nearest_resistance': None,
            'position': 'no_centers',
            'centers_above': 0,
            'centers_below': 0,
            'inside_center': False,
        }

    supports = []    # 中枢下轨 < 当前价 = 支撑
    resistances = []  # 中枢上轨 > 当前价 = 阻力

    for c in centers:
        if c.zd < current_price:
            supports.append(c.zd)
        if c.zg > current_price:
            resistances.append(c.zg)

    supports.sort(reverse=True)
    resistances.sort()

    return {
        'nearest_support': supports[0] if supports else None,
        'nearest_resistance': resistances[0] if resistances else None,
        'position': _determine_position(current_price, supports, resistances, centers),
        'centers_above': len([c for c in centers if c.zd > current_price]),
        'centers_below': len([c for c in centers if c.zg < current_price]),
        'inside_center': any(c.zd <= current_price <= c.zg for c in centers),
    }


def _determine_position(price: float, supports: list, resistances: list,
                        centers: List[Center]) -> str:
    if any(c.zd <= price <= c.zg for c in centers):
        return 'inside'
    if not resistances:
        return 'above_all'
    if not supports:
        return 'below_all'
    return 'between'
