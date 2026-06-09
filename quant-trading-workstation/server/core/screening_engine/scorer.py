"""
选股引擎 — 多因子打分模型
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Factor:
    """因子定义"""
    name: str
    category: str           # 'value'|'profit'|'growth'|'momentum'|'tech'|'quality'|'sentiment'
    weight: float = 1.0     # 默认等权
    higher_better: bool = True  # True=值越大越好, False=越小越好


class MultiFactorScorer:
    """多因子打分引擎"""

    # 默认因子池
    DEFAULT_FACTORS: List[Factor] = field(default_factory=lambda: [
        # 估值因子
        Factor('pe_ttm', 'value', higher_better=False),
        Factor('pb', 'value', higher_better=False),
        Factor('ps_ttm', 'value', higher_better=False),

        # 盈利因子
        Factor('roe', 'profit'),
        Factor('roa', 'profit'),
        Factor('gross_margin', 'profit'),
        Factor('net_margin', 'profit'),

        # 成长因子
        Factor('revenue_yoy', 'growth'),
        Factor('profit_yoy', 'growth'),
        Factor('eps_yoy', 'growth'),

        # 动量因子
        Factor('return_1m', 'momentum'),
        Factor('return_3m', 'momentum'),
        Factor('return_6m', 'momentum'),

        # 技术因子
        Factor('rsi', 'tech'),
        Factor('macd_signal', 'tech'),
        Factor('vol_ratio', 'tech'),

        # 质量因子
        Factor('debt_ratio', 'quality', higher_better=False),
        Factor('cash_ratio', 'quality'),
    ])

    def __init__(self, factors: Optional[List[Factor]] = None):
        self.factors = factors or self.DEFAULT_FACTORS

    def score(self, data: pd.DataFrame) -> pd.Series:
        """
        计算综合打分

        Args:
            data: 包含所有因子数据的 DataFrame
                  每行一只股票，每列一个因子

        Returns:
            每只股票的综合评分 Series (0-100)
        """
        scores = pd.DataFrame(index=data.index)

        for factor in self.factors:
            if factor.name not in data.columns:
                continue

            raw = data[factor.name].dropna()

            # 排名百分位标准化（避免极端值影响）
            ranked = raw.rank(pct=True)

            # 越小越好 → 反转排名
            if not factor.higher_better:
                ranked = 1 - ranked

            # 加权得分
            scores[factor.name] = ranked * factor.weight

        # 计算综合得分并归一化到 0-100
        composite = scores.sum(axis=1)
        composite = (composite - composite.min()) / (composite.max() - composite.min()) * 100

        return composite.round(2)

    def score_by_category(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """按因子类别分别计算得分"""
        categories = {}
        for category in set(f.category for f in self.factors):
            cat_factors = [f for f in self.factors if f.category == category]
            scorer = MultiFactorScorer(cat_factors)
            categories[category] = scorer.score(data)
        return categories
