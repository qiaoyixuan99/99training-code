"""
缠论分析 API 路由 — 完整实现
提供分型/笔/线段/中枢/买卖点多维度分析接口
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from core.data_engine.fetcher import data_fetcher
from core.chan_engine.chan_analyzer import ChanAnalyzer

# 线程池用于并行执行多个缠论分析
_executor = ThreadPoolExecutor(max_workers=4)

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
            '1Y': 'yearly', 'yearly': 'yearly',
        }
        fetch_period = period_map.get(period, period)

        # 根据周期确定日期范围和最大K线数
        period_config = {
            '5m':  {'days': 30,   'max_bars': 500},
            '15m': {'days': 60,   'max_bars': 400},
            '30m': {'days': 90,   'max_bars': 300},
            '60m': {'days': 180,  'max_bars': 300},
            '1d':  {'days': 365*3, 'max_bars': 300},
            'daily': {'days': 365*3, 'max_bars': 300},
            '1w':  {'days': 365*5, 'max_bars': 200},
            'weekly': {'days': 365*5, 'max_bars': 200},
            '1M':  {'days': 365*10, 'max_bars': 120},
            'monthly': {'days': 365*10, 'max_bars': 120},
            '1Y':  {'days': 365*20, 'max_bars': 30},
            'yearly': {'days': 365*20, 'max_bars': 30},
        }
        config = period_config.get(period, {'days': 365*2, 'max_bars': 300})

        if not start_date:
            start_date = (datetime.now() - timedelta(days=config['days'])).strftime('%Y%m%d')
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

        # 限制K线数量
        max_bars = config['max_bars']
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


# ── 多周期批量分析 ──────────────────────────

class BatchPeriodRequest(BaseModel):
    periods: List[str] = ['5m', '30m', '1d', '1w', '1M', '1Y']


@router.post("/batch-analyze/{symbol}")
async def batch_analyze_chan(
    symbol: str,
    body: BatchPeriodRequest,
):
    """
    批量多周期缠论分析 — 一次请求分析多个时段

    解决前端多次请求的性能问题：
    - 后端并行获取数据和分析
    - 使用线程池避免阻塞

    Args:
        symbol: 股票代码
        body.periods: 要分析的周期列表，如 ['5m','30m','1d','1w','1M','1Y']
    """
    try:
        periods = body.periods

        def _analyze_one(p: str) -> dict:
            """同步执行单个周期的分析"""
            try:
                # 复制 analyze_chan_theory 的核心逻辑
                period_map = {
                    '1d': 'daily', 'daily': 'daily',
                    '1w': 'weekly', 'weekly': 'weekly',
                    '1M': 'monthly', 'monthly': 'monthly',
                    '1Y': 'yearly', 'yearly': 'yearly',
                }
                fetch_period = period_map.get(p, p)

                period_config = {
                    '5m':  {'days': 30,   'max_bars': 500},
                    '15m': {'days': 60,   'max_bars': 400},
                    '30m': {'days': 90,   'max_bars': 300},
                    '60m': {'days': 180,  'max_bars': 300},
                    '1d':  {'days': 365*3, 'max_bars': 300},
                    'daily': {'days': 365*3, 'max_bars': 300},
                    '1w':  {'days': 365*5, 'max_bars': 200},
                    'weekly': {'days': 365*5, 'max_bars': 200},
                    '1M':  {'days': 365*10, 'max_bars': 120},
                    'monthly': {'days': 365*10, 'max_bars': 120},
                    '1Y':  {'days': 365*20, 'max_bars': 30},
                    'yearly': {'days': 365*20, 'max_bars': 30},
                }
                config = period_config.get(p, {'days': 365*2, 'max_bars': 300})

                start_date = (datetime.now() - timedelta(days=config['days'])).strftime('%Y%m%d')
                end_date = datetime.now().strftime('%Y%m%d')

                df = data_fetcher.get_kline(
                    symbol=symbol, period=fetch_period,
                    start_date=start_date, end_date=end_date,
                )

                if df.empty:
                    return {'period': p, 'error': f'无数据', 'status': 'empty'}

                if len(df) > config['max_bars']:
                    df = df.tail(config['max_bars'])

                analyzer = ChanAnalyzer(df, symbol=symbol, period=p)
                result = analyzer.run_full_analysis()

                return {
                    'period': p,
                    'status': 'ok',
                    'data_points': result.data_points,
                    'date_range': list(result.date_range),
                    'fractals': result.fractals,
                    'strokes': result.strokes,
                    'segments': result.segments,
                    'centers': result.centers,
                    'buy_points': result.buy_points,
                    'sell_points': result.sell_points,
                    'global_analysis': result.global_analysis,
                    'local_analysis': result.local_analysis,
                    'turning_points': result.turning_points,
                    'anomalies': result.anomalies,
                    'signals': result.signals,
                }
            except Exception as e:
                logger.warning(f"批量分析 {symbol} period={p} 失败: {e}")
                return {'period': p, 'error': str(e), 'status': 'error'}

        # 并行执行（最大4并发，避免对数据源造成压力）
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(_executor, _analyze_one, p)
            for p in periods
        ]
        results = await asyncio.gather(*tasks)

        # 汇总统计
        ok_count = sum(1 for r in results if r.get('status') == 'ok')
        error_count = sum(1 for r in results if r.get('status') == 'error')
        empty_count = sum(1 for r in results if r.get('status') == 'empty')

        logger.info(
            f"批量缠论分析完成: {symbol} "
            f"成功={ok_count} 失败={error_count} 无数据={empty_count}"
        )

        return {
            'symbol': symbol,
            'analyzed_periods': periods,
            'ok_count': ok_count,
            'error_count': error_count,
            'empty_count': empty_count,
            'results': results,
        }

    except Exception as e:
        logger.error(f"批量缠论分析失败 {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
