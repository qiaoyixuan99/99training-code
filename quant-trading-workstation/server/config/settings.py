"""
全局配置
"""
import os


class Settings:
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8001"))
    DEBUG: bool = os.getenv("DEBUG", "1") == "1"

    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "data/quant_trading.db")
    PARQUET_DIR: str = os.getenv("PARQUET_DIR", "data/market")

    DEFAULT_DATA_SOURCE: str = os.getenv("DATA_SOURCE", "akshare")
    TUSHARE_TOKEN: str = os.getenv("TUSHARE_TOKEN", "")

    MAX_BATCH_SYMBOLS: int = 500
    BACKTEST_WORKERS: int = 4

    STRATEGY_DIR: str = os.getenv("STRATEGY_DIR", "strategies")


settings = Settings()
