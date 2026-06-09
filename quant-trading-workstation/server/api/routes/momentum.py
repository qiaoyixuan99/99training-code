"""
动能评分 API 路由
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class MomentumScore(BaseModel):
    symbol: str
    name: str
    total_score: float         # 0-100 综合动能评分
    price_momentum: float      # 价格动能
    volume_momentum: float     # 量能动能
    fund_momentum: float        # 资金动能
    rank: int                  # 全市场排名


class MomentumRanking(BaseModel):
    top_gainers: List[MomentumScore]
    top_losers: List[MomentumScore]
    my_watchlist: List[MomentumScore]


@router.post("/score/{symbol}", response_model=MomentumScore)
async def calculate_score(symbol: str):
    """计算单只股票的动能评分"""
    pass


@router.get("/ranking", response_model=MomentumRanking)
async def get_ranking(
    industry: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
):
    """获取动能排名列表"""
    pass
