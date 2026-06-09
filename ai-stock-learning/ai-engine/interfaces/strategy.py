"""策略接口 — 可插拔的交易策略框架

后续添加新策略只需：
1. 继承 BaseStrategy
2. 实现 analyze() 方法
3. 注册到 StrategyRegistry
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Signal:
    """交易信号"""
    type: str           # 'buy' | 'sell' | 'hold'
    strength: int       # 1-10 信号强度
    price: float        # 信号触发价格
    reason: str         # 信号理由（必须可解释）


@dataclass
class StrategyResult:
    """策略分析结果"""
    strategy_name: str
    signals: List[Signal] = field(default_factory=list)
    confidence: float = 0.0       # 0-1 置信度
    reason: str = ''              # 整体分析依据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'strategy': self.strategy_name,
            'signals': [{'type': s.type, 'strength': s.strength,
                         'price': s.price, 'reason': s.reason} for s in self.signals],
            'confidence': self.confidence,
            'reason': self.reason,
            'metadata': self.metadata,
        }


class BaseStrategy(ABC):
    """交易策略基类

    所有策略必须实现此接口。核心方法 analyze() 接收标准化的
    K线数据和预计算指标，返回结构化的策略分析结果。

    使用示例:
        class MaCrossStrategy(BaseStrategy):
            @property
            def name(self) -> str:
                return '均线金叉策略'

            def analyze(self, klines, indicators):
                # 实现金叉检测逻辑
                ...
                return StrategyResult(...)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称（用于注册和展示）"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """策略描述（一句话说明策略逻辑）"""
        ...

    @abstractmethod
    def analyze(self, klines: List[Any], indicators: Dict[str, Any]) -> StrategyResult:
        """分析K线数据，生成交易信号

        Args:
            klines: K线列表（core.data.KlineBar 对象列表）
            indicators: 预计算的技术指标（core.indicators.compute_all_indicators 的输出）

        Returns:
            StrategyResult: 包含信号列表、置信度和分析依据
        """
        ...

    def __repr__(self) -> str:
        return f'<Strategy: {self.name}>'


class StrategyRegistry:
    """策略注册中心

    管理所有已注册的策略，提供统一的调用接口。

    使用方式:
        registry = StrategyRegistry()
        registry.register(MyStrategy())
        results = registry.run_all(klines, indicators)
    """

    def __init__(self):
        self._strategies: Dict[str, BaseStrategy] = {}

    def register(self, strategy: BaseStrategy) -> None:
        """注册一个策略（同名策略会被覆盖）"""
        if not isinstance(strategy, BaseStrategy):
            raise TypeError(f'策略必须继承 BaseStrategy，收到: {type(strategy)}')
        self._strategies[strategy.name] = strategy

    def unregister(self, name: str) -> None:
        """移除一个策略"""
        self._strategies.pop(name, None)

    def get(self, name: str) -> Optional[BaseStrategy]:
        """获取指定策略"""
        return self._strategies.get(name)

    def list_all(self) -> List[str]:
        """列出所有已注册的策略名称"""
        return list(self._strategies.keys())

    def run_all(self, klines: List[Any], indicators: Dict[str, Any]
                ) -> List[StrategyResult]:
        """运行所有已注册策略，返回结果列表"""
        results = []
        for strategy in self._strategies.values():
            try:
                result = strategy.analyze(klines, indicators)
                results.append(result)
            except Exception as e:
                # 单个策略失败不影响其他策略
                results.append(StrategyResult(
                    strategy_name=strategy.name,
                    signals=[],
                    confidence=0,
                    reason=f'[策略执行失败] {e}',
                ))
        return results

    def run_one(self, name: str, klines: List[Any], indicators: Dict[str, Any]
                ) -> Optional[StrategyResult]:
        """运行指定策略"""
        strategy = self._strategies.get(name)
        if strategy is None:
            return None
        try:
            return strategy.analyze(klines, indicators)
        except Exception as e:
            return StrategyResult(
                strategy_name=name,
                signals=[],
                confidence=0,
                reason=f'[策略执行失败] {e}',
            )

    def __len__(self) -> int:
        return len(self._strategies)

    def __contains__(self, name: str) -> bool:
        return name in self._strategies
