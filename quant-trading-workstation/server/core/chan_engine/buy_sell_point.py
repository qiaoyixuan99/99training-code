"""
缠论引擎 — 买卖点判定模块
基于背驰（MACD背离）识别三类买卖点
"""
import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
from dataclasses import dataclass
from .fractal import Fractal
from .stroke import Stroke
from .segment import Segment
from .center import Center


@dataclass
class BuySellPoint:
    """买卖点数据结构"""
    index: int              # K线索引
    date: any               # 日期
    type: str               # 'buy1'|'buy2'|'buy3'|'sell1'|'sell2'|'sell3'
    price: float            # 价格
    description: str        # 描述
    confidence: float = 0.5 # 置信度 0-1
    divergence_type: str = ''  # 背驰类型


def compute_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    """
    计算 MACD 指标

    Returns:
        DataFrame with columns: dif, dea, macd_bar
    """
    close = df['close'].values
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)

    dif = ema_fast - ema_slow
    dea = _ema(dif, signal)
    macd_bar = 2 * (dif - dea)

    result = df.copy()
    result['dif'] = dif
    result['dea'] = dea
    result['macd_bar'] = macd_bar
    return result


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """指数移动平均"""
    result = np.zeros_like(data)
    result[0] = data[0]
    alpha = 2 / (period + 1)
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result


def detect_buy_sell_points(
    df: pd.DataFrame,
    fractals: List[Fractal],
    strokes: List[Stroke],
    segments: List[Segment],
    centers: List[Center],
) -> Tuple[List[BuySellPoint], List[BuySellPoint]]:
    """
    识别三类买卖点

    第一类买点：下跌趋势终结，底背驰确认
    第一类卖点：上涨趋势终结，顶背驰确认

    第二类买点：第一类买点后回抽不破新低（次级别二买）
    第二类卖点：第一类卖点后反弹不破新高（次级别二卖）

    第三类买点：向上离开中枢后回抽不破中枢ZG
    第三类卖点：向下离开中枢后反弹不破中枢ZD

    Args:
        df: 原始K线DataFrame
        fractals: 分型列表
        strokes: 笔列表
        segments: 线段列表
        centers: 中枢列表

    Returns:
        (buy_points, sell_points)
    """
    df_macd = compute_macd(df)

    buy_points = []
    sell_points = []

    # —— 第一类买卖点：基于线段背驰 ——
    bp1, sp1 = _detect_type1_points(df_macd, strokes, segments, fractals)
    buy_points.extend(bp1)
    sell_points.extend(sp1)

    # —— 第二类买卖点：基于第一类之后的回抽 ——
    bp2, sp2 = _detect_type2_points(df_macd, buy_points, sell_points, strokes, fractals)
    buy_points.extend(bp2)
    sell_points.extend(sp2)

    # —— 第三类买卖点：基于中枢突破回抽 ——
    bp3, sp3 = _detect_type3_points(df_macd, centers, strokes, fractals)
    buy_points.extend(bp3)
    sell_points.extend(sp3)

    # 按时间排序
    buy_points.sort(key=lambda x: x.index)
    sell_points.sort(key=lambda x: x.index)

    return buy_points, sell_points


def _detect_type1_points(
    df: pd.DataFrame, strokes: List[Stroke],
    segments: List[Segment], fractals: List[Fractal]
) -> Tuple[List[BuySellPoint], List[BuySellPoint]]:
    """
    第一类买卖点：基于 MACD 背驰判断

    底背驰（第一类买点）：
    - 价格创新低（当前底分型低点 < 前一个底分型低点）
    - MACD DIF 不创新低（当前DIF > 前低DIF）
    - 或绿柱面积缩小

    顶背驰（第一类卖点）：
    - 价格创新高（当前顶分型高点 > 前一个顶分型高点）
    - MACD DIF 不创新高（当前DIF < 前高DIF）
    - 或红柱面积缩小
    """
    buy_points = []
    sell_points = []

    # 使用笔作为判断单元
    for i in range(1, len(strokes)):
        curr = strokes[i]
        prev = strokes[i - 1]

        if curr.direction == 'down':
            # 下降笔：寻找底背驰（买入信号）
            # 找向前一个同向笔比较
            prev_down = None
            for j in range(i - 2, -1, -1):
                if strokes[j].direction == 'down':
                    prev_down = strokes[j]
                    break

            if prev_down is not None and curr.end_price < prev_down.end_price:
                # 价格创新低，检查MACD是否背驰
                curr_dif = _get_macd_at(df, curr.end_index, 'dif')
                prev_dif = _get_macd_at(df, prev_down.end_index, 'dif')

                if curr_dif is not None and prev_dif is not None:
                    if curr_dif > prev_dif:  # DIF底背驰
                        desc = (
                            f"【第一类买点】下跌背驰：价格从{prev_down.end_price:.2f}跌至"
                            f"{curr.end_price:.2f}创新低，但MACD DIF从{prev_dif:.4f}升至"
                            f"{curr_dif:.4f}不创新低，下跌动能衰竭"
                        )
                        buy_points.append(BuySellPoint(
                            index=curr.end_index,
                            date=curr.end_date,
                            type='buy1',
                            price=curr.end_price,
                            description=desc,
                            confidence=0.75,
                            divergence_type='bottom_divergence',
                        ))

        elif curr.direction == 'up':
            # 上升笔：寻找顶背驰（卖出信号）
            prev_up = None
            for j in range(i - 2, -1, -1):
                if strokes[j].direction == 'up':
                    prev_up = strokes[j]
                    break

            if prev_up is not None and curr.end_price > prev_up.end_price:
                curr_dif = _get_macd_at(df, curr.end_index, 'dif')
                prev_dif = _get_macd_at(df, prev_up.end_index, 'dif')

                if curr_dif is not None and prev_dif is not None:
                    if curr_dif < prev_dif:  # DIF顶背驰
                        desc = (
                            f"【第一类卖点】上涨背驰：价格从{prev_up.end_price:.2f}涨至"
                            f"{curr.end_price:.2f}创新高，但MACD DIF从{prev_dif:.4f}降至"
                            f"{curr_dif:.4f}不创新高，上涨动能衰竭"
                        )
                        sell_points.append(BuySellPoint(
                            index=curr.end_index,
                            date=curr.end_date,
                            type='sell1',
                            price=curr.end_price,
                            description=desc,
                            confidence=0.75,
                            divergence_type='top_divergence',
                        ))

    return buy_points, sell_points


def _detect_type2_points(
    df: pd.DataFrame, buy_points: List[BuySellPoint],
    sell_points: List[BuySellPoint], strokes: List[Stroke],
    fractals: List[Fractal]
) -> Tuple[List[BuySellPoint], List[BuySellPoint]]:
    """
    第二类买卖点：第一类买卖点之后的回抽确认

    第二类买点：一买之后，价格回落但未破一买低点
    第二类卖点：一卖之后，价格反弹但未破一卖高点
    """
    buy2 = []
    sell2 = []

    # 基于一买找二买
    for bp in buy_points[:3]:  # 只取前几个一买
        # 在一买之后寻找回抽底分型
        for f in fractals:
            if f.index > bp.index and f.type == 'bottom':
                if f.low > bp.price:  # 未破新低
                    # 检查是否在合理区间（一买后5-30根K线）
                    distance = f.index - bp.index
                    if 5 <= distance <= 60:
                        desc = (
                            f"【第二类买点】一买({bp.price:.2f})后回抽确认："
                            f"价格回落到{f.low:.2f}未破前低，确认底部有效"
                        )
                        buy2.append(BuySellPoint(
                            index=f.index,
                            date=f.date,
                            type='buy2',
                            price=f.low,
                            description=desc,
                            confidence=0.65,
                        ))
                        break  # 只取最近的一个

    # 基于一卖找二卖
    for sp in sell_points[:3]:
        for f in fractals:
            if f.index > sp.index and f.type == 'top':
                if f.high < sp.price:  # 未破新高
                    distance = f.index - sp.index
                    if 5 <= distance <= 60:
                        desc = (
                            f"【第二类卖点】一卖({sp.price:.2f})后反弹确认："
                            f"价格反弹到{f.high:.2f}未破前高，确认顶部有效"
                        )
                        sell2.append(BuySellPoint(
                            index=f.index,
                            date=f.date,
                            type='sell2',
                            price=f.high,
                            description=desc,
                            confidence=0.65,
                        ))
                        break

    return buy2, sell2


def _detect_type3_points(
    df: pd.DataFrame, centers: List[Center],
    strokes: List[Stroke], fractals: List[Fractal]
) -> Tuple[List[BuySellPoint], List[BuySellPoint]]:
    """
    第三类买卖点：中枢突破后的回抽

    第三类买点：向上突破中枢后，回抽不破中枢上轨(ZG)
    第三类卖点：向下跌破中枢后，反弹不破中枢下轨(ZD)
    """
    buy3 = []
    sell3 = []

    for center in centers:
        # 寻找向上突破中枢的笔
        for stroke in strokes:
            if stroke.direction == 'up' and stroke.start_index > center.end_index:
                if stroke.end_price > center.zg:
                    # 向上突破中枢，找后续回抽
                    for f in fractals:
                        if f.index > stroke.end_index and f.type == 'bottom':
                            if f.low >= center.zg * 0.98:  # 回抽不破ZG（留2%容差）
                                desc = (
                                    f"【第三类买点】突破中枢({center.zg:.2f}-{center.zd:.2f})后，"
                                    f"回抽至{f.low:.2f}不破中枢上轨{center.zg:.2f}，上行确认"
                                )
                                buy3.append(BuySellPoint(
                                    index=f.index,
                                    date=f.date,
                                    type='buy3',
                                    price=f.low,
                                    description=desc,
                                    confidence=0.7,
                                ))
                                break
                    break  # 只取该中枢的第一次突破

        # 寻找向下跌破中枢的笔
        for stroke in strokes:
            if stroke.direction == 'down' and stroke.start_index > center.end_index:
                if stroke.end_price < center.zd:
                    for f in fractals:
                        if f.index > stroke.end_index and f.type == 'top':
                            if f.high <= center.zd * 1.02:  # 反弹不破ZD（留2%容差）
                                desc = (
                                    f"【第三类卖点】跌破中枢({center.zg:.2f}-{center.zd:.2f})后，"
                                    f"反弹至{f.high:.2f}不破中枢下轨{center.zd:.2f}，下行确认"
                                )
                                sell3.append(BuySellPoint(
                                    index=f.index,
                                    date=f.date,
                                    type='sell3',
                                    price=f.high,
                                    description=desc,
                                    confidence=0.7,
                                ))
                                break
                    break

    return buy3, sell3


def _get_macd_at(df: pd.DataFrame, index: int, col: str) -> Optional[float]:
    """安全获取指定位置的MACD值"""
    if index < len(df) and index >= 0:
        val = df[col].iloc[index]
        if not np.isnan(val) and not np.isinf(val):
            return float(val)
    return None
