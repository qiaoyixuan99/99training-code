"""
大盘择时 API 路由
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class TimingSignal(BaseModel):
    index_code: str          # 指数代码
    index_name: str
    signal: str              # 'BUY' | 'HOLD' | 'SELL'
    confidence: float        # 信号置信度 0-1
    score: int               # 综合得分
    details: List[dict]      # 各子指标得分明细


class TimingHistory(BaseModel):
    date: str
    signal: str
    score: int


@router.get("/signal", response_model=TimingSignal)
async def get_timing_signal(
    index_code: str = Query("sh.000001", description="指数代码，默认上证综指"),
):
    """
    获取大盘择时信号
    综合多指标投票：均线趋势+MACD+布林带+ADX+RSI+成交量+市场宽度
    """
    pass


@router.get("/history", response_model=List[TimingHistory])
async def get_timing_history(
    index_code: str = "sh.000001",
    limit: int = Query(100, ge=1, le=500),
):
    """获取历史择时信号"""
    pass
