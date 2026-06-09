"""
策略基类接口 — 所有用户策略必须实现此接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


class StrategyBase(ABC):
    """
    策略基类

    用户编写策略时继承此类，实现 init() 和 next() 方法。

    使用示例：
        class MyStrategy(StrategyBase):
            params = {'fast': 5, 'slow': 20}

            def init(self):
                # 预计算指标
                self.fast_ma = self.data['close'].rolling(self.params['fast']).mean()
                self.slow_ma = self.data['close'].rolling(self.params['slow']).mean()

            def next(self, i):
                # 每根K线的交易逻辑
                if self.fast_ma[i] > self.slow_ma[i] and not self.has_position():
                    self.buy(percent=0.5)  # 半仓买入
                elif self.fast_ma[i] < self.slow_ma[i] and self.has_position():
                    self.sell()  # 清仓卖出
    """

    params: Dict[str, Any] = {}

    def __init__(self, data: pd.DataFrame, capital: float = 100_000):
        """
        Args:
            data: K线数据 [open, high, low, close, volume] 索引为日期
            capital: 初始资金
        """
        self.data = data
        self.capital = capital
        self.cash = capital
        self.position = 0  # 持仓数量（股）
        self.position_value = 0.0
        self._signals = np.zeros(len(data))  # 交易信号记录

    @abstractmethod
    def init(self):
        """初始化：预计算指标，只执行一次"""
        ...

    @abstractmethod
    def next(self, i: int):
        """
        每根K线触发（从第1根开始，i=0为初始状态）

        Args:
            i: 当前K线索引位置
        """
        ...

    # ---- 交易操作 ----

    def buy(self, percent: float = 1.0, price: Optional[float] = None):
        """
        买入操作

        Args:
            percent: 买入资金比例 (0~1)
            price: 买入价格，None 则使用当前K线收盘价
        """
        # 在向量化回测中标记信号为买入
        ...

    def sell(self, percent: float = 1.0, price: Optional[float] = None):
        """
        卖出操作

        Args:
            percent: 卖出持仓比例 (0~1)
            price: 卖出价格，None 则使用当前K线收盘价
        """
        ...

    # ---- 状态查询 ----

    def has_position(self) -> bool:
        """是否有持仓"""
        return self.position > 0

    def current_price(self, i: int, field: str = 'close') -> float:
        """获取当前K线的价格"""
        return float(self.data.iloc[i][field])

    # ---- 风控 ----

    def set_stop_loss(self, price: float):
        """设置止损价"""
        ...

    def set_take_profit(self, price: float):
        """设置止盈价"""
        ...

    # ---- 日志 ----

    def log(self, msg: str):
        """记录策略日志"""
        print(f"[Strategy] {msg}")
