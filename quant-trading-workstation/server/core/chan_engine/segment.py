"""
缠论引擎 — 线段构建模块
由笔构建线段，识别特征序列并判断线段终结
"""
import numpy as np
from typing import List, Optional
from dataclasses import dataclass
from .stroke import Stroke


@dataclass
class Segment:
    """线段数据结构"""
    start_index: int           # 起始K线索引
    end_index: int             # 结束K线索引
    direction: str             # 'up' | 'down'
    strokes: List[int]         # 包含的笔索引列表
    start_price: float
    end_price: float
    start_date: any
    end_date: any
    high: float                # 线段最高价
    low: float                 # 线段最低价
    stroke_count: int          # 包含的笔数
    strength: float = 0.0      # 线段力度


def build_segments(strokes: List[Stroke], df_original) -> List[Segment]:
    """
    基于笔构建线段

    线段规则：
    1. 至少由3笔组成（奇数笔）
    2. 相邻笔必须有重叠区间
    3. 线段方向由第一笔方向决定
    4. 线段终结：出现反向线段特征时

    简化实现：
    - 找到相邻笔的重叠区间
    - 当反向笔突破前高/前低时，判断线段终结
    - 确保线段由至少3笔组成

    Args:
        strokes: 已验证的笔列表
        df_original: 原始K线DataFrame

    Returns:
        线段列表
    """
    if len(strokes) < 3:
        return []

    segments = []
    i = 0

    while i < len(strokes):
        # 尝试从第i笔开始构建线段
        seg_strokes = [i]
        direction = strokes[i].direction
        current_high = strokes[i].high
        current_low = strokes[i].low
        seg_start = i
        terminated = False

        j = i + 1
        while j < len(strokes):
            s = strokes[j]

            if s.direction == direction:
                # 同向笔：检查是否继续延伸
                if direction == 'up':
                    if s.high > current_high:
                        seg_strokes.append(j)
                        current_high = s.high
                        current_low = max(current_low, s.low)
                    else:
                        # 同向笔但没创新高，检查是否终结
                        # 如果前一笔的方向已经有足够多的笔，可能线段已结束
                        if len(seg_strokes) >= 3:
                            terminated = True
                            break
                        seg_strokes.append(j)
                else:  # down
                    if s.low < current_low:
                        seg_strokes.append(j)
                        current_low = s.low
                        current_high = min(current_high, s.high)
                    else:
                        if len(seg_strokes) >= 3:
                            terminated = True
                            break
                        seg_strokes.append(j)
            else:
                # 反向笔：检查是否与线段有重叠
                has_overlap = _check_stroke_overlap(
                    strokes, seg_strokes, j,
                    current_high, current_low
                )
                if has_overlap or len(seg_strokes) < 3:
                    seg_strokes.append(j)
                elif len(seg_strokes) >= 3:
                    # 无重叠且已有3笔，线段终结
                    break

            j += 1

        # 确保至少3笔才构成线段
        if len(seg_strokes) >= 3:
            seg = _create_segment(strokes, seg_strokes, df_original)
            segments.append(seg)
            i = seg_strokes[-1]  # 从最后一笔继续
        else:
            i += 1

        if not terminated and j >= len(strokes):
            break

    return segments


def _check_stroke_overlap(
    strokes: List[Stroke], seg_stroke_indices: List[int],
    new_idx: int, current_high: float, current_low: float
) -> bool:
    """检查新笔是否与线段内笔有重叠"""
    new_stroke = strokes[new_idx]
    # 新的反向笔的最高价需要高于线段区间低点，最低价需要低于线段区间高点
    return new_stroke.high > current_low and new_stroke.low < current_high


def _create_segment(
    strokes: List[Stroke], seg_stroke_indices: List[int], df_original
) -> Segment:
    """创建线段对象"""
    seg_strokes_list = [strokes[i] for i in seg_stroke_indices]

    first_s = seg_strokes_list[0]
    last_s = seg_strokes_list[-1]

    # 线段方向由第一笔方向决定
    direction = first_s.direction

    # 计算线段极值
    segment_high = max(s.high for s in seg_strokes_list)
    segment_low = min(s.low for s in seg_strokes_list)

    # 起点价格
    start_price = first_s.start_price
    end_price = last_s.end_price

    # 力度
    strength = abs(end_price - start_price) / start_price if start_price > 0 else 0

    return Segment(
        start_index=first_s.start_index,
        end_index=last_s.end_index,
        direction=direction,
        strokes=seg_stroke_indices,
        start_price=start_price,
        end_price=end_price,
        start_date=first_s.start_date,
        end_date=last_s.end_date,
        high=segment_high,
        low=segment_low,
        stroke_count=len(seg_stroke_indices),
        strength=round(strength * 100, 4),
    )


def detect_segment_divergence(segments: List[Segment]) -> List[dict]:
    """
    检测线段背驰（线段级别背离）

    比较相邻同向线段的力度（价格变动幅度）
    如果新线段价格创新高/新低但力度减弱 → 背驰

    Returns:
        背驰信号列表 [{'segment_idx': int, 'type': 'top_divergence'|'bottom_divergence'}, ...]
    """
    divergences = []

    for i in range(2, len(segments)):
        prev = segments[i - 2]
        curr = segments[i]

        if curr.direction != prev.direction:
            continue

        if curr.direction == 'up':
            # 上升线段：价格创新高但力度减弱 = 顶背驰
            if curr.end_price > prev.end_price and curr.strength < prev.strength:
                divergences.append({
                    'segment_idx': i,
                    'type': 'top_divergence',
                    'prev_strength': prev.strength,
                    'curr_strength': curr.strength,
                    'price_new_high': True,
                })
        else:
            # 下降线段：价格创新低但力度减弱 = 底背驰
            if curr.end_price < prev.end_price and curr.strength < prev.strength:
                divergences.append({
                    'segment_idx': i,
                    'type': 'bottom_divergence',
                    'prev_strength': prev.strength,
                    'curr_strength': curr.strength,
                    'price_new_low': True,
                })

    return divergences
