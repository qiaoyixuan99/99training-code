"""K线数据获取层 — 东方财富API封装 + 数据类定义"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import requests
import json
import os
import time

# 周期映射：输入key → 东方财富API klt参数
PERIOD_MAP: Dict[str, str] = {
    '5min':  '5',
    '15min': '15',
    '30min': '30',
    '60min': '60',
    'day':   '101',
    'week':  '102',
    'month': '103',
}

PERIOD_LABELS: Dict[str, str] = {
    '5min': '5分钟', '15min': '15分钟', '30min': '30分钟',
    '60min': '60分钟', 'day': '日K', 'week': '周K', 'month': '月K',
}

# 东方财富API端点
API_KLINE = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
API_QUOTE = 'https://push2.eastmoney.com/api/qt/stock/get'
API_SEARCH = 'https://searchadapter.eastmoney.com/api/suggest/get'

# 请求超时（秒）
REQUEST_TIMEOUT = 10

# 模拟浏览器请求头（东方财富API会验证）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://quote.eastmoney.com/',
    'Connection': 'close',
}

# 全局 Session（禁用SSL验证 + 每次请求后关闭连接，避免东方财富CDN断开问题）
_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    """获取或创建请求Session（禁用SSL验证以兼容东方财富CDN）"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.verify = False
        _session.headers.update(HEADERS)
        # 禁用urllib3的SSL警告
        import urllib3
        urllib3.disable_warnings()
    return _session


@dataclass
class KlineBar:
    """单根K线数据"""
    time: str           # 日期字符串 "2026-06-09"
    open: float
    close: float
    high: float
    low: float
    volume: float       # 成交量（手）
    amount: float       # 成交额（元）
    amplitude: float = 0.0    # 振幅%
    change_pct: float = 0.0   # 涨跌幅%
    change: float = 0.0       # 涨跌额
    turnover: float = 0.0     # 换手率%

    @property
    def is_up(self) -> bool:
        return self.close >= self.open

    @property
    def body(self) -> float:
        """实体大小"""
        return abs(self.close - self.open)

    @property
    def upper_shadow(self) -> float:
        """上影线长度"""
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> float:
        """下影线长度"""
        return min(self.open, self.close) - self.low

    @property
    def body_ratio(self) -> float:
        """实体占比 (实体/总波幅)"""
        total = self.high - self.low
        return self.body / total if total > 0 else 0

    def to_dict(self) -> dict:
        return {
            'time': self.time,
            'open': self.open,
            'close': self.close,
            'high': self.high,
            'low': self.low,
            'volume': self.volume,
            'amount': self.amount,
            'amplitude': self.amplitude,
            'change_pct': self.change_pct,
            'change': self.change,
            'turnover': self.turnover,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'KlineBar':
        """从字典创建KlineBar（兼容小程序端字段名）"""
        return cls(
            time=d.get('time', ''),
            open=float(d.get('open', 0)),
            close=float(d.get('close', 0)),
            high=float(d.get('high', 0)),
            low=float(d.get('low', 0)),
            volume=float(d.get('volume', 0)),
            amount=float(d.get('amount', 0)),
            amplitude=float(d.get('amplitude', 0) or d.get('amplitude', 0)),
            change_pct=float(d.get('changePct', 0) or d.get('change_pct', 0)),
            change=float(d.get('change', 0)),
            turnover=float(d.get('turnover', 0)),
        )

    @classmethod
    def from_dict_array(cls, data: List[dict]) -> List['KlineBar']:
        """从字典数组批量创建KlineBar列表"""
        return [cls.from_dict(d) for d in data]


@dataclass
class QuoteSnapshot:
    """实时行情快照"""
    code: str
    name: str
    price: float
    open: float
    high: float
    low: float
    volume: float
    amount: float
    change: float
    change_pct: float
    turnover: float = 0.0

    def to_dict(self) -> dict:
        return {
            'code': self.code, 'name': self.name,
            'price': self.price, 'open': self.open,
            'high': self.high, 'low': self.low,
            'volume': self.volume, 'amount': self.amount,
            'change': self.change, 'change_pct': self.change_pct,
            'turnover': self.turnover,
        }


def _get_secid(code: str) -> str:
    """根据股票代码生成东方财富secid"""
    if not code or not isinstance(code, str):
        return '0.000001'
    code = code.strip()
    if code.startswith('6'):
        return f'1.{code}'   # 上海
    return f'0.{code}'       # 深圳


def _get_market(code: str) -> int:
    """0=深圳, 1=上海"""
    if code.startswith('6'):
        return 1
    return 0


class KlineDataFetcher:
    """K线数据获取器 — 东方财富API + 本地缓存"""

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), '..', '.cache')
        self._cache_dir = cache_dir
        self._cache_ttl = 300  # 缓存有效期5分钟
        os.makedirs(self._cache_dir, exist_ok=True)

    def _cache_path(self, code: str, period: str, count: int) -> str:
        return os.path.join(self._cache_dir, f'{code}_{period}_{count}.json')

    def _read_cache(self, code: str, period: str, count: int) -> Optional[List[KlineBar]]:
        path = self._cache_path(code, period, count)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if time.time() - data.get('ts', 0) > self._cache_ttl:
                return None
            return [KlineBar(**b) for b in data['klines']]
        except Exception:
            return None

    def _write_cache(self, code: str, period: str, count: int, klines: List[KlineBar]):
        try:
            path = self._cache_path(code, period, count)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    'ts': time.time(),
                    'klines': [k.to_dict() for k in klines],
                }, f, ensure_ascii=False)
        except Exception:
            pass  # 缓存写入失败不阻塞

    def fetch_kline(self, code: str, period: str = 'day', count: int = 200,
                    use_cache: bool = True) -> List[KlineBar]:
        """获取K线数据

        Args:
            code: 股票代码，如 '000001' (平安银行)
            period: 周期 ('day','week','month','60min','30min','15min','5min')
            count: 获取条数
            use_cache: 是否使用缓存
        """
        if use_cache:
            cached = self._read_cache(code, period, count)
            if cached:
                return cached

        klt = PERIOD_MAP.get(period, '101')
        secid = _get_secid(code)

        try:
            resp = _get_session().get(API_KLINE, params={
                'secid': secid,
                'klt': klt,
                'fqt': 1,         # 前复权
                'beg': '0',
                'end': '20500000',
                'lmt': count,
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            }, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f'获取K线数据失败 [{code}]: {e}')

        if not data.get('data') or not data['data'].get('klines'):
            raise RuntimeError(f'K线数据为空 [{code}]，请检查股票代码')

        klines_raw = data['data']['klines']
        klines = []
        for line in klines_raw:
            parts = line.split(',')
            klines.append(KlineBar(
                time=parts[0],
                open=float(parts[1]),
                close=float(parts[2]),
                high=float(parts[3]),
                low=float(parts[4]),
                volume=float(parts[5]),
                amount=float(parts[6]),
                amplitude=float(parts[7]) if len(parts) > 7 else 0,
                change_pct=float(parts[8]) if len(parts) > 8 else 0,
                change=float(parts[9]) if len(parts) > 9 else 0,
                turnover=float(parts[10]) if len(parts) > 10 else 0,
            ))

        if use_cache:
            self._write_cache(code, period, count, klines)

        return klines

    def fetch_quote(self, code: str) -> QuoteSnapshot:
        """获取实时行情快照"""
        secid = _get_secid(code)

        try:
            resp = _get_session().get(API_QUOTE, params={
                'secid': secid,
                'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f168,f169,f170',
            }, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            d = resp.json()['data']
        except Exception as e:
            raise RuntimeError(f'获取行情失败 [{code}]: {e}')

        return QuoteSnapshot(
            code=code,
            name=d.get('f58', ''),
            price=d.get('f43', 0) / 100,
            open=d.get('f46', 0) / 100,
            high=d.get('f44', 0) / 100,
            low=d.get('f45', 0) / 100,
            volume=d.get('f47', 0),
            amount=d.get('f48', 0),
            change=d.get('f169', 0) / 100,
            change_pct=d.get('f170', 0) / 100,
            turnover=d.get('f168', 0) / 100,
        )

    def search(self, keyword: str) -> List[dict]:
        """搜索股票"""
        try:
            resp = _get_session().get(API_SEARCH, params={
                'input': keyword,
                'type': 14,
                'token': 'DEFAULT',
                'count': 10,
            }, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f'搜索失败: {e}')

        if not data.get('QuotationCodeTable', {}).get('Data'):
            return []

        results = []
        for item in data['QuotationCodeTable']['Data']:
            if item.get('StockType') in ('A', 'ETF'):
                results.append({
                    'code': item['Code'],
                    'name': item['Name'],
                    'market': 'sh' if item.get('Market') == 'SA' else 'sz',
                    'type': item['StockType'],
                })
        return results
