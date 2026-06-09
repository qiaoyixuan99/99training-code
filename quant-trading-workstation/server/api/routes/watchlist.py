"""
自选股 API 路由
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class WatchlistItem(BaseModel):
    id: Optional[int] = None
    symbol: str
    name: Optional[str] = None
    group: str = "默认"
    sort_order: int = 0


class WatchlistGroup(BaseModel):
    name: str
    count: int


@router.get("/list", response_model=List[WatchlistItem])
async def get_watchlist(group: Optional[str] = None):
    """获取自选股列表"""
    pass


@router.post("/add")
async def add_stock(item: WatchlistItem):
    """添加自选股"""
    pass


@router.delete("/remove/{symbol}")
async def remove_stock(symbol: str):
    """删除自选股"""
    pass


@router.put("/update/{symbol}")
async def update_stock(symbol: str, item: WatchlistItem):
    """更新自选股信息（分组/排序）"""
    pass


@router.get("/groups", response_model=List[WatchlistGroup])
async def get_groups():
    """获取所有分组"""
    pass


@router.post("/groups/create")
async def create_group(name: str):
    """创建新分组"""
    pass
