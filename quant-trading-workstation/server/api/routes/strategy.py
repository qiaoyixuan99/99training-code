"""
策略管理 API 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class StrategyMeta(BaseModel):
    id: Optional[int] = None
    name: str
    description: str = ""
    code: str
    params: Optional[dict] = None


class StrategyListItem(BaseModel):
    id: int
    name: str
    description: str
    updated_at: str


@router.get("/list", response_model=List[StrategyListItem])
async def list_strategies():
    """获取所有策略列表"""
    pass


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: int):
    """获取单个策略详情（含代码）"""
    pass


@router.post("/save")
async def save_strategy(strategy: StrategyMeta):
    """保存策略（新建或更新）"""
    pass


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int):
    """删除策略"""
    pass


@router.post("/validate")
async def validate_code(code: str):
    """校验策略 Python 代码语法"""
    try:
        compile(code, "<strategy>", "exec")
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {"valid": False, "error": f"Line {e.lineno}: {e.msg}"}


@router.get("/templates")
async def get_templates():
    """获取内置策略模板"""
    return [
        {"name": "双均线交叉", "file": "ma_cross.py"},
        {"name": "缠论策略", "file": "chan_theory_strategy.py"},
        {"name": "动量突破", "file": "momentum_breakout.py"},
        {"name": "海龟交易", "file": "turtle_trading.py"},
        {"name": "布林带策略", "file": "bollinger_bands.py"},
        {"name": "MACD策略", "file": "macd_strategy.py"},
    ]
