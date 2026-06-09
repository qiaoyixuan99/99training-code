"""预测接口 — 可插拔的预测模型框架

后续添加预测模型只需：
1. 继承 BasePredictor
2. 实现 predict() 方法
3. 注册到 PredictorRegistry

支持的预测模型类型（示例）：
- 技术面预测：基于指标规则（方向 + 目标价）
- ML预测：LSTM / XGBoost 等模型
- LLM预测：Claude API 分析 + 预测
- 混合预测：组合多个子模型
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class PredictionResult:
    """预测结果"""
    predictor_name: str
    direction: str                # 'up' | 'down' | 'sideways'
    target_price: Optional[float] = None   # 预测目标价
    confidence: float = 0.0       # 0-1 置信度
    horizon: int = 5              # 预测周期（K线根数）
    reason: str = ''              # 预测依据（必须可解释）
    risk_level: str = 'medium'    # 'low' | 'medium' | 'high'
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'predictor': self.predictor_name,
            'direction': self.direction,
            'target_price': self.target_price,
            'confidence': self.confidence,
            'horizon': self.horizon,
            'reason': self.reason,
            'risk_level': self.risk_level,
            'metadata': self.metadata,
        }


class BasePredictor(ABC):
    """预测模型基类

    所有预测模型必须实现此接口。核心方法 predict() 接收 K线数据
    和预计算指标，返回结构化的预测结果。

    使用示例:
        class TrendPredictor(BasePredictor):
            @property
            def name(self) -> str:
                return '趋势预测器'

            @property
            def description(self) -> str:
                return '基于均线排列和MACD的趋势方向预测'

            def predict(self, klines, indicators):
                trend = indicators.get('trend', {})
                return PredictionResult(
                    predictor_name=self.name,
                    direction='up' if trend.get('score', 50) > 60 else 'down',
                    confidence=0.6,
                    horizon=5,
                    reason=f"趋势评分: {trend.get('score', 'N/A')}",
                )
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """预测器名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """预测器描述"""
        ...

    @property
    @abstractmethod
    def horizon(self) -> int:
        """默认预测周期（K线根数）"""
        ...

    @abstractmethod
    def predict(self, klines: List[Any], indicators: Dict[str, Any]) -> PredictionResult:
        """基于K线数据和指标生成预测

        Args:
            klines: K线列表（core.data.KlineBar 对象列表）
            indicators: 预计算的技术指标字典

        Returns:
            PredictionResult: 包含方向、目标价、置信度等
        """
        ...

    def __repr__(self) -> str:
        return f'<Predictor: {self.name}>'


class PredictorRegistry:
    """预测器注册中心

    管理所有已注册的预测模型，提供统一的调用接口。

    使用方式:
        registry = PredictorRegistry()
        registry.register(TrendPredictor())
        results = registry.run_all(klines, indicators)
    """

    def __init__(self):
        self._predictors: Dict[str, BasePredictor] = {}

    def register(self, predictor: BasePredictor) -> None:
        """注册一个预测器"""
        if not isinstance(predictor, BasePredictor):
            raise TypeError(f'预测器必须继承 BasePredictor，收到: {type(predictor)}')
        self._predictors[predictor.name] = predictor

    def unregister(self, name: str) -> None:
        """移除一个预测器"""
        self._predictors.pop(name, None)

    def get(self, name: str) -> Optional[BasePredictor]:
        """获取指定预测器"""
        return self._predictors.get(name)

    def list_all(self) -> List[str]:
        """列出所有已注册的预测器"""
        return list(self._predictors.keys())

    def run_all(self, klines: List[Any], indicators: Dict[str, Any]
                ) -> List[PredictionResult]:
        """运行所有已注册的预测器"""
        results = []
        for predictor in self._predictors.values():
            try:
                result = predictor.predict(klines, indicators)
                results.append(result)
            except Exception as e:
                results.append(PredictionResult(
                    predictor_name=predictor.name,
                    direction='sideways',
                    confidence=0,
                    reason=f'[预测执行失败] {e}',
                ))
        return results

    def run_one(self, name: str, klines: List[Any], indicators: Dict[str, Any]
                ) -> Optional[PredictionResult]:
        """运行指定预测器"""
        predictor = self._predictors.get(name)
        if predictor is None:
            return None
        try:
            return predictor.predict(klines, indicators)
        except Exception as e:
            return PredictionResult(
                predictor_name=name,
                direction='sideways',
                confidence=0,
                reason=f'[预测执行失败] {e}',
            )

    def __len__(self) -> int:
        return len(self._predictors)

    def __contains__(self, name: str) -> bool:
        return name in self._predictors
