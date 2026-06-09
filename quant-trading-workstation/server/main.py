"""
QuantTrading Workstation — 服务入口
"""
import sys
import os

# 确保当前目录在 sys.path 中（支持从任意位置运行）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from loguru import logger

from config.settings import settings
from api.routes import (
    market_data, screening, backtest, strategy,
    chan_theory, momentum, timing, watchlist
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("QuantTrading Workstation 启动中...")
    yield
    logger.info("QuantTrading Workstation 关闭")


def create_app() -> FastAPI:
    app = FastAPI(
        title="QuantTrading Workstation API",
        description="一体化量化交易辅助平台后端服务",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(market_data.router, prefix="/api/v1/market", tags=["行情数据"])
    app.include_router(screening.router, prefix="/api/v1/screener", tags=["智能选股"])
    app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["策略回测"])
    app.include_router(strategy.router, prefix="/api/v1/strategy", tags=["策略管理"])
    app.include_router(chan_theory.router, prefix="/api/v1/chan-theory", tags=["缠论分析"])
    app.include_router(momentum.router, prefix="/api/v1/momentum", tags=["动能评分"])
    app.include_router(timing.router, prefix="/api/v1/timing", tags=["大盘择时"])
    app.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["自选股"])

    # 前端静态页面
    PKG_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    APP_HTML = os.path.join(PKG_ROOT, "desktop", "app.html")
    STATIC_DIR = os.path.join(PKG_ROOT, "desktop", "static")
    CHART_JS = os.path.join(STATIC_DIR, "lightweight-charts.js")

    @app.get("/static/lightweight-charts.js")
    async def serve_chart_js():
        if os.path.isfile(CHART_JS):
            return FileResponse(CHART_JS, media_type="application/javascript")
        from fastapi import HTTPException
        raise HTTPException(404, detail="chart library not found")

    @app.get("/")
    async def root():
        if os.path.exists(APP_HTML):
            return FileResponse(APP_HTML)
        return {"message": "QuantTrading Workstation API", "docs": "/docs"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
