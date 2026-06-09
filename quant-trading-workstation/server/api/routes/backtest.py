"""
回测 API 路由
"""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


class BacktestRequest(BaseModel):
    strategy_code: str
    symbols: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 100_000
    commission: float = 0.0003
    slippage: float = 0.001
    params: Optional[dict] = None


class BacktestSummary(BaseModel):
    symbol: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    win_rate: float
    max_drawdown: float
    trade_count: int


@router.post("/run")
async def run_backtest(req: BacktestRequest, background_tasks: BackgroundTasks):
    """
    执行回测（支持单只和批量）
    300只股票全历史目标 < 3分钟
    """
    # TODO: 异步执行回测任务
    return {"message": "ok", "task_id": "bt_xxx"}


@router.get("/result/{task_id}")
async def get_result(task_id: str):
    """获取回测结果"""
    # TODO: 返回回测绩效指标
    pass


@router.get("/history")
async def get_history(limit: int = 20):
    """获取历史回测记录"""
    pass


@router.post("/optimize")
async def optimize_params(req: BacktestRequest):
    """参数优化（网格搜索/遗传算法）"""
    pass
