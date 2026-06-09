"""
数据引擎 — 多数据源统一适配器
主力: Baostock (免费A股数据，稳定)
补充: AKShare (数据更全，但网络受限时不可用)
"""
import pandas as pd
from typing import List, Optional, Dict
from datetime import datetime
from loguru import logger


class DataFetcher:
    """统一数据获取接口"""

    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
        self._bs_login = False

    def _ensure_baostock_login(self):
        """确保 Baostock 已登录"""
        if not self._bs_login:
            import baostock as bs
            lg = bs.login()
            if lg.error_code == '0':
                self._bs_login = True
                logger.info("Baostock 登录成功")
            else:
                logger.error(f"Baostock 登录失败: {lg.error_msg}")

    # ── K线数据 ──────────────────────────────

    def get_kline(
        self,
        symbol: str,
        period: str = "1d",
        start_date: str = "20230101",
        end_date: Optional[str] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        获取股票历史K线数据

        Args:
            symbol: 股票代码，如 '600000' 或 '000001'
            period: 周期，支持 'daily'(日)/'weekly'(周)/'monthly'(月)
                    以及分时 '5m'/'15m'/'30m'/'60m'
            start_date: 开始日期 'YYYYMMDD'
            end_date: 结束日期 'YYYYMMDD'，默认今天
            use_cache: 是否使用缓存
        """
        end_date = end_date or datetime.now().strftime("%Y%m%d")
        cache_key = f"{symbol}:{period}:{start_date}:{end_date}"

        if use_cache and cache_key in self._cache:
            logger.debug(f"缓存命中: {symbol}")
            return self._cache[cache_key].copy()

        # 分时数据只走 AKShare
        if period in ('5m', '15m', '30m', '60m', '1m'):
            df = self._fetch_akshare_intraday(symbol, period, start_date, end_date)
            self._cache[cache_key] = df
            return df

        # 年K数据：获取月K后聚合
        if period in ('1Y', 'yearly'):
            df = self._fetch_yearly_kline(symbol, start_date, end_date)
            self._cache[cache_key] = df
            return df

        # 日线/周线/月线数据优先 Baostock（网络兼容性好），失败则回退 AKShare
        try:
            df = self._fetch_baostock_kline(symbol, period, start_date, end_date)
            self._cache[cache_key] = df
            return df
        except Exception as e1:
            logger.warning(f"Baostock 获取 {symbol} K线失败: {e1}，尝试 AKShare...")
            try:
                df = self._fetch_akshare_kline(symbol, period, start_date, end_date)
                self._cache[cache_key] = df
                return df
            except Exception as e2:
                logger.error(f"所有数据源均失败 {symbol}: {e2}")
                raise

    def get_index_kline(
        self,
        index_code: str,
        period: str = "daily",
        start_date: str = "20230101",
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """获取指数K线数据"""
        end_date = end_date or datetime.now().strftime("%Y%m%d")
        import akshare as ak

        index_map = {
            "sh.000001": "sh000001",  # 上证综指
            "sz.399001": "sz399001",  # 深证成指
            "sz.399006": "sz399006",  # 创业板指
            "sh.000688": "sh000688",  # 科创50
        }
        code = index_map.get(index_code, index_code.replace(".", ""))

        df = ak.stock_zh_index_daily(symbol=code)
        return self._normalize_columns(df)

    # ── 股票列表 ──────────────────────────────

    def get_stock_list(self) -> pd.DataFrame:
        """获取全量A股列表"""
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            df = df.rename(columns={"code": "symbol", "name": "name"})
            return df
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise

    # ── 私有方法 ──────────────────────────────

    def _fetch_baostock_kline(
        self, symbol: str, period: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """通过 Baostock 获取个股K线"""
        import baostock as bs

        self._ensure_baostock_login()

        # 确定股票代码前缀
        code = symbol
        if symbol.startswith("6") or symbol.startswith("9"):
            bs_symbol = f"sh.{symbol}"
        elif symbol.startswith("0") or symbol.startswith("3") or symbol.startswith("2"):
            bs_symbol = f"sz.{symbol}"
        else:
            bs_symbol = f"sh.{symbol}"

        # Baostock 周期映射
        period_map = {"daily": "d", "1d": "d", "weekly": "w", "1w": "w", "monthly": "m", "1M": "m"}
        bs_period = period_map.get(period, "d")

        # 日期格式转换: YYYYMMDD → YYYY-MM-DD
        start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

        rs = bs.query_history_k_data_plus(
            bs_symbol,
            "date,open,high,low,close,volume,amount",
            start_date=start, end_date=end,
            frequency=bs_period,
            adjustflag="2",  # 前复权
        )

        if rs.error_code != '0':
            raise RuntimeError(f"Baostock 查询失败: {rs.error_msg}")

        rows = []
        while rs.next():
            rows.append(rs.get_row_data())

        if not rows:
            raise ValueError(f"Baostock 未获取到 {symbol} 的数据")

        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume", "amount"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()

        # 转换数据类型
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype("int64")

        # 过滤空值行
        df = df.dropna(subset=["open", "high", "low", "close"])

        if df.empty:
            raise ValueError(f"{symbol} 数据为空（可能停牌或退市）")

        return df[["open", "high", "low", "close", "volume"]]

    def _fetch_akshare_kline(
        self, symbol: str, period: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """通过 AKShare 获取个股K线"""
        import akshare as ak

        # AKShare 周期映射
        period_map = {
            "1d": "daily", "daily": "daily",
            "1w": "weekly", "weekly": "weekly",
            "1M": "monthly", "monthly": "monthly",
        }

        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period=period_map.get(period, "daily"),
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",  # 前复权
        )

        if df is None or df.empty:
            raise ValueError(f"未获取到 {symbol} 的数据")

        return self._normalize_columns(df)

    def _fetch_akshare_intraday(
        self, symbol: str, period: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """通过 AKShare 获取分时K线数据（5m/15m/30m/60m）"""
        import akshare as ak

        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period.replace('m', ''),
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
        except Exception:
            # 部分AKShare版本 period参数用字母
            period_map = {'5m': '5', '15m': '15', '30m': '30', '60m': '60', '1m': '1'}
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period_map.get(period, '5'),
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )

        if df is None or df.empty:
            raise ValueError(f"未获取到 {symbol} 分时数据 (period={period})")

        return self._normalize_columns(df)

    def _fetch_yearly_kline(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """获取年K线数据（通过月K聚合）"""
        import numpy as np

        # 确保获取足够长的月K数据（至少15年用于有效年K聚合）
        from datetime import datetime, timedelta
        extended_start = start_date
        try:
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            extended_dt = max(
                datetime(2000, 1, 1),
                start_dt - timedelta(days=365 * 10)
            )
            extended_start = extended_dt.strftime('%Y%m%d')
        except (ValueError, TypeError):
            extended_start = (datetime.now() - timedelta(days=365 * 20)).strftime('%Y%m%d')

        # 先获取月K数据（使用单独的缓存键避免循环）
        monthly_cache_key = f"{symbol}:monthly:{extended_start}:{end_date}"
        if monthly_cache_key in self._cache:
            monthly = self._cache[monthly_cache_key].copy()
        else:
            monthly = self.get_kline(
                symbol=symbol, period='monthly',
                start_date=extended_start, end_date=end_date,
                use_cache=False,
            )
            self._cache[monthly_cache_key] = monthly

        if monthly.empty:
            raise ValueError(f"无法获取 {symbol} 的月K数据从而聚合年K")

        # 按月聚合为年
        monthly = monthly.copy()
        monthly['year'] = monthly.index.year

        yearly_rows = []
        for year, group in monthly.groupby('year'):
            yearly_rows.append({
                'open': group['open'].iloc[0],
                'high': group['high'].max(),
                'low': group['low'].min(),
                'close': group['close'].iloc[-1],
                'volume': group['volume'].sum(),
            })

        result = pd.DataFrame(
            yearly_rows,
            index=pd.to_datetime([f"{y}-12-31" for y in sorted(monthly['year'].unique())])
        ).sort_index()

        if result.empty:
            raise ValueError(f"{symbol} 年K聚合后为空")

        return result[['open', 'high', 'low', 'close', 'volume']]

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名 — 中文 → 英文"""
        col_map = {
            "日期": "date", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume",
            "成交额": "amount", "换手率": "turnover",
            "振幅": "amplitude", "涨跌幅": "pct_change",
            "涨跌额": "change", "股票代码": "symbol",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()

        # 确保关键列存在
        required_cols = ["open", "high", "low", "close", "volume"]
        available = [c for c in required_cols if c in df.columns]
        if len(available) < 4:
            raise ValueError(f"数据列不完整，仅有: {list(df.columns)}")

        return df[available]


# 全局单例
data_fetcher = DataFetcher()
