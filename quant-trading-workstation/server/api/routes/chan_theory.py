"""
缠论分析 API 路由 — 完整实现
提供分型/笔/线段/中枢/买卖点多维度分析接口
"""
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from core.data_engine.fetcher import data_fetcher
from core.chan_engine.chan_analyzer import ChanAnalyzer

router = APIRouter()


class FractalPoint(BaseModel):
    index: int
    date: str
    type: str
    high: float
    low: float


class Stroke(BaseModel):
    start_index: int
    end_index: int
    start_date: str
    end_date: str
    direction: str
    start_price: float
    end_price: float
    high: float
    low: float
    kline_count: int
    strength: float


class Segment(BaseModel):
    start_index: int
    end_index: int
    start_date: str
    end_date: str
    direction: str
    start_price: float
    end_price: float
    high: float
    low: float
    stroke_count: int
    strength: float
    strokes: List[int]


class Center(BaseModel):
    zg: float
    zd: float
    zz: float
    start_index: int
    end_index: int
    start_date: str
    end_date: str
    level: str
    strength: float
    kline_count: int
    segments: List[int]


class BuySellPoint(BaseModel):
    index: int
    date: str
    type: str
    price: float
    description: str
    confidence: float
    divergence_type: str = ''


class TurningPointDetail(BaseModel):
    index: int
    date: str
    type: str
    price: float
    local_high: float
    local_low: float
    local_range_pct: float
    volume_ratio: float
    trend_position: str
    level: str
    is_stroke_endpoint: bool
    is_segment_endpoint: bool
    anomalies: List[str]


class AnomalyItem(BaseModel):
    index: int
    date: str
    type: str
    description: str
    severity: str


class Signal(BaseModel):
    index: int
    date: str
    direction: str
    type: str
    price: float
    description: str
    confidence: float
    source: str


class GlobalAnalysisResult(BaseModel):
    trend: str
    trend_strength: float
    phase: str
    multi_period_resonance: str
    key_support: float
    key_resistance: float
    structure_health: float
    has_segment_divergence: bool
    segment_divergences: List[Dict]
    center_gravity: Dict
    fractal_count: int
    stroke_count: int
    segment_count: int
    center_count: int
    summary: str


class LocalAnalysisResult(BaseModel):
    current_trend: str
    current_price: float
    nearest_fractal: Optional[Dict]
    nearest_center: Optional[Dict]
    pending_signals: List[str]
    risk_level: str
    distance_to_support: float
    distance_to_resistance: float


class ChanAnalysisResult(BaseModel):
    symbol: str
    period: str
    data_points: int
    date_range: List[str]

    fractals: List[Dict]
    strokes: List[Dict]
    segments: List[Dict]
    centers: List[Dict]
    buy_points: List[Dict]
    sell_points: List[Dict]

    global_analysis: Dict
    local_analysis: Dict
    turning_points: List[Dict]
    anomalies: List[Dict]
    signals: List[Dict]


@router.post("/analyze/{symbol}", response_model=ChanAnalysisResult)
async def analyze_chan_theory(
    symbol: str,
    period: str = Query("1d", description="分析周期 5m/15m/30m/60m/1d/1w/1M"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """
    执行缠论完整多维度分析：分型 → 笔 → 线段 → 中枢 → 买卖点

    返回包含：
    - 全局趋势分析（多维度趋势、市场阶段、结构健康度）
    - 局部分析（当前趋势、风险等级、支撑/阻力距离）
    - 拐点详细分析（每个分型的局部特征、趋势位置、异常标记）
    - 异常点检测（量能异常、价格缺口、背驰、假突破、异常振幅）
    - 买卖信号汇总（一类/二类/三类买卖点）
    """
    try:
        # 确定数据周期
        period_map = {
            '1d': 'daily', 'daily': 'daily',
            '1w': 'weekly', 'weekly': 'weekly',
            '1M': 'monthly', 'monthly': 'monthly',
        }
        fetch_period = period_map.get(period, period)

        # 默认获取最近300根K线
        if not start_date:
            if period in ('5m', '15m', '30m', '60m'):
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            else:
                start_date = (datetime.now() - timedelta(days=365 * 2)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')

        df = data_fetcher.get_kline(
            symbol=symbol,
            period=fetch_period,
            start_date=start_date,
            end_date=end_date,
        )

        if df.empty:
            raise HTTPException(status_code=404, detail=f"未获取到 {symbol} 的K线数据")

        # 限制K线数量（缠论分析需要适量数据）
        max_bars = 500 if period in ('5m', '15m', '30m', '60m') else 300
        if len(df) > max_bars:
            df = df.tail(max_bars)

        logger.info(f"开始缠论分析: {symbol} period={period} bars={len(df)}")

        # 执行完整分析
        analyzer = ChanAnalyzer(df, symbol=symbol, period=period)
        result = analyzer.run_full_analysis()

        logger.info(
            f"缠论分析完成: {symbol} "
            f"分型={result.global_analysis['fractal_count']} "
            f"笔={result.global_analysis['stroke_count']} "
            f"段={result.global_analysis['segment_count']} "
            f"中枢={result.global_analysis['center_count']} "
            f"买点={len(result.buy_points)} "
            f"卖点={len(result.sell_points)} "
            f"异常={len(result.anomalies)}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"缠论分析失败 {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quick/{symbol}")
async def quick_chan_analysis(
    symbol: str,
    period: str = "1d",
):
    """
    快速缠论分析（仅返回关键信号和位置）
    """
    try:
        result = await analyze_chan_theory(
            symbol=symbol,
            period=period,
        )
        return {
            'symbol': result.symbol,
            'period': result.period,
            'date_range': result.date_range,
            'global_trend': result.global_analysis['trend'],
            'phase': result.global_analysis['phase'],
            'structure_health': result.global_analysis['structure_health'],
            'risk_level': result.local_analysis['risk_level'],
            'current_price': result.local_analysis['current_price'],
            'key_support': result.global_analysis['key_support'],
            'key_resistance': result.global_analysis['key_resistance'],
            'buy_signals': [
                {'type': s['type'], 'price': s['price'], 'date': s['date'], 'confidence': s['confidence']}
                for s in result.signals if s['direction'] == 'buy'
            ],
            'sell_signals': [
                {'type': s['type'], 'price': s['price'], 'date': s['date'], 'confidence': s['confidence']}
                for s in result.signals if s['direction'] == 'sell'
            ],
            'pending_signals': result.local_analysis['pending_signals'],
            'recent_anomalies': [
                a for a in result.anomalies
                if a['severity'] == 'high'
            ][:5],
            'summary': result.global_analysis['summary'],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"快速缠论分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/points/{symbol}")
async def get_buy_sell_points(
    symbol: str,
    period: str = "1d",
):
    """
    仅获取买卖点列表（快速查询）
    """
    try:
        result = await analyze_chan_theory(symbol=symbol, period=period)
        return {
            'symbol': result.symbol,
            'period': result.period,
            'buy_points': result.buy_points,
            'sell_points': result.sell_points,
            'current_price': result.local_analysis['current_price'],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取买卖点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies/{symbol}")
async def get_anomalies(
    symbol: str,
    period: str = "1d",
):
    """
    获取异常点列表
    """
    try:
        result = await analyze_chan_theory(symbol=symbol, period=period)
        return {
            'symbol': result.symbol,
            'period': result.period,
            'total_anomalies': len(result.anomalies),
            'anomalies': result.anomalies,
            'turning_points_with_anomalies': [
                tp for tp in result.turning_points
                if tp.get('anomalies') and len(tp['anomalies']) > 0
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取异常点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/turning-points/{symbol}")
async def get_turning_points(
    symbol: str,
    period: str = "1d",
):
    """
    获取所有拐点详细分析
    """
    try:
        result = await analyze_chan_theory(symbol=symbol, period=period)
        return {
            'symbol': result.symbol,
            'period': result.period,
            'total_turning_points': len(result.turning_points),
            'major_points': [tp for tp in result.turning_points if tp['level'] == 'major'],
            'medium_points': [tp for tp in result.turning_points if tp['level'] == 'medium'],
            'minor_points': [tp for tp in result.turning_points if tp['level'] == 'minor'],
            'all_points': result.turning_points,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取拐点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
