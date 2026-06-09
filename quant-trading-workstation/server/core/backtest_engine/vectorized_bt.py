"""
回测引擎 — 向量化回测核心
目标：300只股票全历史 < 3分钟
"""
import numpy as np
import pandas as pd
from numba import jit
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable


@dataclass
class BacktestParams:
    """回测参数"""
    start_date: str
    end_date: str
    initial_capital: float = 100_000
    commission: float = 0.0003        # 万三手续费
    slippage: float = 0.001          # 千一滑点
    stop_loss: Optional[float] = None # 止损比例
    take_profit: Optional[float] = None
    allow_short: bool = False         # 是否允许做空


@dataclass
class BacktestResult:
    """回测结果"""
    total_return: float
    annual_return: float
    sharpe_ratio: float
    win_rate: float
    max_drawdown: float
    calmar_ratio: float
    profit_loss_ratio: float
    trade_count: int
    equity_curve: np.ndarray
    trades: pd.DataFrame
    monthly_returns: pd.DataFrame


class VectorizedBacktester:
    """向量化回测引擎 — 高性能核心"""

    def __init__(self, params: BacktestParams):
        self.params = params

    def run(self, data: pd.DataFrame, signals: pd.Series) -> BacktestResult:
        """
        执行向量化回测

        Args:
            data: DataFrame with columns [open, high, low, close, volume]
            signals: Series of trading signals (1=buy, -1=sell, 0=hold)

        Returns:
            BacktestResult with all performance metrics
        """
        # 计算每日收益率
        returns = data['close'].pct_change().fillna(0)

        # 向量化持仓计算
        positions = signals.shift(1).fillna(0)

        # 策略收益率 = 持仓 × 市场收益率
        strategy_returns = positions * returns

        # 扣除交易成本
        trades = signals.diff().abs().fillna(0)
        costs = trades * (self.params.commission + self.params.slippage)
        strategy_returns = strategy_returns - costs

        # 资金曲线
        equity_curve = (1 + strategy_returns).cumprod() * self.params.initial_capital

        # 计算绩效指标
        return self._compute_metrics(equity_curve, strategy_returns, signals)

    def run_batch(
        self,
        data_dict: Dict[str, pd.DataFrame],
        signal_func: Callable[[pd.DataFrame], pd.Series],
    ) -> Dict[str, BacktestResult]:
        """批量回测多只股票"""
        results = {}
        for symbol, data in data_dict.items():
            signals = signal_func(data)
            results[symbol] = self.run(data, signals)
        return results

    def _compute_metrics(
        self,
        equity: pd.Series,
        returns: pd.Series,
        signals: pd.Series,
    ) -> BacktestResult:
        """计算所有绩效指标"""
        # 总收益
        total_return = equity.iloc[-1] / self.params.initial_capital - 1

        # 年化收益率
        years = len(returns) / 252
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # 夏普比率（假设无风险利率=0.02）
        excess = returns - 0.02 / 252
        sharpe = np.sqrt(252) * excess.mean() / excess.std() if excess.std() > 0 else 0

        # 胜率
        winning = returns[returns > 0]
        all_trades = returns[returns != 0]
        win_rate = len(winning) / len(all_trades) if len(all_trades) > 0 else 0

        # 最大回撤
        cummax = equity.cummax()
        drawdown = (equity - cummax) / cummax
        max_dd = drawdown.min()

        # 卡尔玛比率
        calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

        # 盈亏比
        avg_win = winning.mean() if len(winning) > 0 else 0
        losing = returns[returns < 0]
        avg_loss = abs(losing.mean()) if len(losing) > 0 else 1e-10
        pl_ratio = avg_win / avg_loss

        # 交易次数
        trade_count = int(signals.diff().abs().sum() / 2)

        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            max_drawdown=max_dd,
            calmar_ratio=calmar,
            profit_loss_ratio=pl_ratio,
            trade_count=trade_count,
            equity_curve=equity.values,
            trades=pd.DataFrame(),  # TODO: 交易明细
            monthly_returns=pd.DataFrame(),  # TODO: 月度收益
        )


# Numba 加速的热点函数
@jit(nopython=True)
def _compute_equity_fast(close: np.ndarray, signals: np.ndarray, capital: float) -> np.ndarray:
    """Numba JIT 加速的资金曲线计算"""
    n = len(close)
    equity = np.zeros(n)
    equity[0] = capital
    position = 0

    for i in range(1, n):
        ret = (close[i] - close[i-1]) / close[i-1]
        equity[i] = equity[i-1] * (1 + position * ret)
        position = signals[i]

    return equity
