"""
行情数据 API 路由 — 已实现
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from loguru import logger

from core.data_engine.fetcher import data_fetcher

router = APIRouter()


@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    period: str = Query("daily", description="daily / weekly / monthly / 5m / 15m / 30m / 60m / yearly"),
    limit: int = Query(500, ge=1, le=5000),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """
    获取股票历史K线数据

    示例: GET /api/v1/market/kline/600000?period=daily&limit=100
    """
    try:
        # 根据周期确定合适的日期范围
        if not start_date:
            period_days = {
                '5m': 30, '15m': 60, '30m': 90, '60m': 180, '1m': 10,
                'daily': limit * 3, '1d': limit * 3,
                'weekly': limit * 7, '1w': limit * 7,
                'monthly': limit * 31, '1M': limit * 31,
                'yearly': 365 * 20, '1Y': 365 * 20,
            }
            days = period_days.get(period, limit * 2)
            start = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        else:
            start = start_date
        end = end_date or datetime.now().strftime('%Y%m%d')

        df = data_fetcher.get_kline(
            symbol=symbol,
            period=period,
            start_date=start,
            end_date=end,
        )

        # 取最近 limit 条
        df = df.tail(limit)

        # DataFrame → JSON
        records = []
        for idx, row in df.iterrows():
            records.append({
                "date": idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10],
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "volume": int(row["volume"]),
            })

        return {
            "symbol": symbol,
            "period": period,
            "count": len(records),
            "data": records,
        }

    except Exception as e:
        logger.error(f"获取K线失败 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-list")
async def get_stock_list():
    """获取全量A股列表"""
    try:
        df = data_fetcher.get_stock_list()
        return {
            "count": len(df),
            "data": df.head(100).to_dict(orient="records"),
            "note": "仅返回前100条预览",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _parse_sina_realtime(symbol: str) -> Optional[dict]:
    """从新浪财经获取实时行情（交易日盘中可用）"""
    try:
        import httpx
        prefix = "sh" if (symbol.startswith("6") or symbol.startswith("9")) else "sz"
        url = f"http://hq.sinajs.cn/list={prefix}{symbol}"
        headers = {"Referer": "http://finance.sina.com.cn"}
        resp = httpx.get(url, headers=headers, timeout=5.0)
        resp.encoding = "gbk"
        text = resp.text
        start = text.find('"') + 1
        end = text.rfind('"')
        if start <= 0 or end <= start or len(text[start:end].split(",")) < 30:
            return None
        f = text[start:end].split(",")
        return {
            "symbol": symbol,
            "name": f[0],
            "open": round(float(f[1]), 2) if f[1] else 0,
            "yesterday_close": round(float(f[2]), 2) if f[2] else 0,
            "price": round(float(f[3]), 2) if f[3] else 0,
            "high": round(float(f[4]), 2) if f[4] else 0,
            "low": round(float(f[5]), 2) if f[5] else 0,
            "volume": int(float(f[8])) if f[8] else 0,
            "amount": round(float(f[9]), 2) if f[9] else 0,
            "date": f[30],
            "time": f[31],
            "source": "sina_realtime",
        }
    except Exception:
        return None


@router.get("/realtime/{symbol}")
async def get_realtime(symbol: str):
    """获取实时行情（优先新浪，回退日线）"""
    # 先尝试新浪实时数据
    rt = _parse_sina_realtime(symbol)
    if rt is not None and rt.get("price", 0) > 0:
        return rt

    # 回退：取最近一根日线
    try:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
        df = data_fetcher.get_kline(symbol=symbol, start_date=start, end_date=end)
        if df.empty:
            return {"symbol": symbol, "available": False}
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        return {
            "symbol": symbol,
            "name": "",
            "date": str(df.index[-1])[:10],
            "open": round(float(latest["open"]), 2),
            "high": round(float(latest["high"]), 2),
            "low": round(float(latest["low"]), 2),
            "close": round(float(latest["close"]), 2),
            "price": round(float(latest["close"]), 2),
            "volume": int(latest["volume"]),
            "yesterday_close": round(float(prev["close"]), 2),
            "change": round(float(latest["close"] - prev["close"]), 2),
            "change_pct": round(float((latest["close"] - prev["close"]) / prev["close"] * 100), 2),
            "source": "baostock_eod",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
