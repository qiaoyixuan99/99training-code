"""综合分析引擎 — 编排数据获取、指标计算、形态识别、策略/预测调用"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .data import KlineBar, KlineDataFetcher, QuoteSnapshot, PERIOD_MAP, PERIOD_LABELS
from .indicators import compute_all_indicators
from .patterns import detect_all_patterns

# 延迟导入接口模块（避免循环依赖）
from interfaces.strategy import StrategyRegistry, StrategyResult
from interfaces.predictor import PredictorRegistry, PredictionResult


class KlineAnalyzer:
    """K线综合分析引擎

    编排完整的分析流程：获取数据 → 计算指标 → 识别形态 → 运行策略/预测 → 生成报告

    使用方式:
        analyzer = KlineAnalyzer()

        # 基础分析（不运行策略/预测）
        report = analyzer.analyze('000001', 'day')

        # 注册策略后分析
        analyzer.strategies.register(MyStrategy())
        report = analyzer.analyze('000001', 'day')

        # 只获取数据+指标
        data = analyzer.fetch_and_compute('000001', 'day')
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self._fetcher = KlineDataFetcher(cache_dir=cache_dir)

        # 策略和预测注册中心（公开属性，方便外部注册）
        self.strategies = StrategyRegistry()
        self.predictors = PredictorRegistry()

    # ---- 核心 API ----

    def fetch_and_compute(self, code: str, period: str = 'day', count: int = 200
                          ) -> Dict[str, Any]:
        """获取K线数据并计算所有指标+形态

        Args:
            code: 股票代码
            period: K线周期
            count: K线条数
        Returns:
            {'klines': [...], 'indicators': {...}, 'patterns': {...}, 'quote': {...}}
        """
        klines = self._fetcher.fetch_kline(code, period, count)
        return self.fetch_and_compute_data(klines, code, period)

    def fetch_and_compute_data(self, klines: List[KlineBar], code: str = '',
                                period: str = 'day') -> Dict[str, Any]:
        """对已有的K线数据计算指标+形态（不发起网络请求）"""
        indicators = compute_all_indicators(klines)
        patterns = detect_all_patterns(klines)

        # 尝试获取实时行情
        quote = None
        if code:
            try:
                quote = self._fetcher.fetch_quote(code)
            except Exception:
                pass

        return {
            'code': code,
            'period': period,
            'period_label': PERIOD_LABELS.get(period, period),
            'klines': klines,
            'indicators': indicators,
            'patterns': patterns,
            'quote': quote,
        }

    def analyze(self, code: str, period: str = 'day', count: int = 200
                ) -> Dict[str, Any]:
        """完整分析流程，返回结构化报告

        这是主入口方法。无论是否注册了策略/预测器，都会返回基础分析结果。
        如果注册了策略/预测器，会同时运行它们并包含在报告中。
        """
        data = self.fetch_and_compute(code, period, count)
        return self.analyze_from_data(
            data['klines'], data, code, period,
            stock_name=data['quote'].name if data['quote'] else '',
        )

    def analyze_from_data(self, klines: List[KlineBar], data: Dict[str, Any],
                           code: str = '', period: str = 'day',
                           stock_name: str = '',
                           latest_override: Optional[Dict[str, Any]] = None
                           ) -> Dict[str, Any]:
        """从已有数据生成完整分析报告（不发起网络请求）

        Args:
            klines: K线数据列表
            data: fetch_and_compute 或 fetch_and_compute_data 的输出
            code: 股票代码
            period: K线周期
            stock_name: 股票名称
            latest_override: 可选，覆盖最新价和涨跌幅 {'price': ..., 'change_pct': ...}
        """
        indicators = data['indicators']
        patterns = data['patterns']
        quote = data.get('quote')

        # 基础分析
        summary = self._build_summary(klines, indicators, patterns)

        # 运行已注册的策略
        strategy_results: List[StrategyResult] = []
        if len(self.strategies) > 0:
            strategy_results = self.strategies.run_all(klines, indicators)

        # 运行已注册的预测器
        prediction_results: List[PredictionResult] = []
        if len(self.predictors) > 0:
            prediction_results = self.predictors.run_all(klines, indicators)

        # 风险提示
        risk = self._assess_risk(klines, indicators, patterns)

        # 构建完整报告
        # 处理最新价覆盖（来自小程序端的实时行情）
        latest_price = klines[-1].close if klines else 0
        latest_change = klines[-1].change_pct if klines else 0
        if latest_override:
            if latest_override.get('price') is not None:
                latest_price = latest_override['price']
            if latest_override.get('change_pct') is not None:
                latest_change = latest_override['change_pct']

        report = {
            'meta': {
                'code': code,
                'period': period,
                'period_label': data['period_label'],
                'stock_name': stock_name or (quote.name if quote else ''),
                'analyzed_at': datetime.now().isoformat(),
                'klines_count': len(klines),
                'latest_time': klines[-1].time if klines else '',
                'latest_price': latest_price,
                'latest_change_pct': latest_change,
                'strategies_loaded': len(self.strategies),
                'predictors_loaded': len(self.predictors),
            },
            'quote': quote.to_dict() if quote else None,
            'summary': summary,
            'indicators': indicators,
            'patterns': {
                'trend': patterns['trend'],
                'levels': patterns['levels'],
                'latest_signals': patterns['latest_signals'],
                # 完整形态数据（仅保留最近出现的）
                'doji_count': len(patterns['doji']),
                'hammer_count': len(patterns['hammer']),
                'engulfing_count': len(patterns['engulfing']),
            },
            'risk': risk,
            'strategy_results': [r.to_dict() for r in strategy_results],
            'prediction_results': [r.to_dict() for r in prediction_results],
        }

        return report

    # ---- 内部方法 ----

    def _build_summary(self, klines: List[KlineBar], indicators: Dict[str, Any],
                       patterns: Dict[str, Any]) -> Dict[str, Any]:
        """构建综合分析摘要"""
        trend = patterns['trend']
        levels = patterns['levels']

        # MA状态
        ma = indicators.get('ma', {})
        ma_status = self._describe_ma(ma, klines[-1].close)

        # MACD状态
        macd = indicators.get('macd', {})
        macd_status = self._describe_macd(macd)

        # RSI状态
        rsi = indicators.get('rsi', {})
        rsi_status = self._describe_rsi(rsi)

        # 关键价位
        latest = klines[-1].close
        dist_support = None
        dist_resistance = None
        if levels.get('nearest_support'):
            dist_support = round((latest - levels['nearest_support']) / latest * 100, 2)
        if levels.get('nearest_resistance'):
            dist_resistance = round((levels['nearest_resistance'] - latest) / latest * 100, 2)

        # 生成多空判断
        bullish_signals = []
        bearish_signals = []

        if trend['score'] >= 60:
            bullish_signals.append(f"趋势偏多（{trend['overall']}）")
        elif trend['score'] <= 40:
            bearish_signals.append(f"趋势偏空（{trend['overall']}）")

        if rsi_status['rsi14'] is not None:
            if rsi_status['rsi14'] < 30:
                bullish_signals.append(f"RSI超卖（{rsi_status['rsi14']}），有反弹需求")
            elif rsi_status['rsi14'] > 70:
                bearish_signals.append(f"RSI超买（{rsi_status['rsi14']}），有回调压力")

        if macd_status.get('signal') == 'golden_cross':
            bullish_signals.append('MACD金叉')
        elif macd_status.get('signal') == 'dead_cross':
            bearish_signals.append('MACD死叉')

        # 综合评分 (0-100，越高越看多)
        score = 50
        score += (trend['score'] - 50) * 0.4
        if rsi_status['rsi14'] is not None:
            score += (50 - rsi_status['rsi14']) * 0.2  # 超卖加分，超买减分
        if macd_status.get('signal') == 'golden_cross':
            score += 10
        elif macd_status.get('signal') == 'dead_cross':
            score -= 10
        score = max(0, min(100, round(score)))

        return {
            'score': score,
            'bias': 'bullish' if score > 55 else 'bearish' if score < 45 else 'neutral',
            'trend': trend,
            'ma_status': ma_status,
            'macd_status': macd_status,
            'rsi_status': rsi_status,
            'levels': {
                'nearest_support': levels.get('nearest_support'),
                'nearest_resistance': levels.get('nearest_resistance'),
                'dist_support_pct': dist_support,
                'dist_resistance_pct': dist_resistance,
            },
            'bullish_signals': bullish_signals,
            'bearish_signals': bearish_signals,
        }

    def _describe_ma(self, ma: Dict[str, Any], price: float) -> Dict[str, Any]:
        """描述均线状态"""
        ma5 = ma.get('ma5')
        ma10 = ma.get('ma10')
        ma20 = ma.get('ma20')
        ma60 = ma.get('ma60')

        arrangement = 'unknown'
        if all(v is not None for v in [ma5, ma10, ma20]):
            if ma5 > ma10 > ma20:
                arrangement = '多头排列'
            elif ma5 < ma10 < ma20:
                arrangement = '空头排列'
            else:
                arrangement = '缠绕'

        return {
            'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
            'arrangement': arrangement,
            'price_above_ma20': price > ma20 if ma20 else None,
            'price_above_ma60': price > ma60 if ma60 else None,
        }

    def _describe_macd(self, macd: Dict[str, Any]) -> Dict[str, Any]:
        """描述MACD状态"""
        dif = macd.get('dif')
        dea = macd.get('dea')
        hist = macd.get('histogram')

        signal = None
        if dif is not None and dea is not None:
            if dif > dea and dif > 0:
                signal = 'bullish'
            elif dif < dea and dif < 0:
                signal = 'bearish'
            elif dif > dea:
                signal = 'golden_cross_potential'
            else:
                signal = 'dead_cross_potential'

        # 判断是否刚金叉/死叉（基于 histogram 符号变化）
        cross = None
        if hist is not None:
            if hist > 0:
                cross = 'above_zero'
            else:
                cross = 'below_zero'

        return {
            'dif': dif,
            'dea': dea,
            'histogram': hist,
            'signal': signal,
            'histogram_position': cross,
        }

    def _describe_rsi(self, rsi_data: Dict[str, Any]) -> Dict[str, Any]:
        """描述RSI状态"""
        rsi14 = rsi_data.get('rsi14')
        status = 'neutral'
        if rsi14 is not None:
            if rsi14 > 80:
                status = '严重超买'
            elif rsi14 > 70:
                status = '超买'
            elif rsi14 < 20:
                status = '严重超卖'
            elif rsi14 < 30:
                status = '超卖'
            elif rsi14 > 50:
                status = '偏强'
            else:
                status = '偏弱'

        return {
            'rsi6': rsi_data.get('rsi6'),
            'rsi14': rsi14,
            'rsi24': rsi_data.get('rsi24'),
            'status': status,
        }

    def _assess_risk(self, klines: List[KlineBar], indicators: Dict[str, Any],
                     patterns: Dict[str, Any]) -> Dict[str, Any]:
        """风险评估"""
        warnings = []

        # 1. 波动率风险
        atr_pct = indicators.get('atr_pct')
        if atr_pct is not None:
            if atr_pct > 5:
                warnings.append({'level': 'high', 'msg': f'波动率极高（ATR={atr_pct}%），注意仓位控制'})
            elif atr_pct > 3:
                warnings.append({'level': 'medium', 'msg': f'波动率偏高（ATR={atr_pct}%）'})

        # 2. 成交量异常
        vol = indicators.get('volume', {})
        vol_ratio = vol.get('volume_ratio', 1)
        if vol_ratio > 3:
            warnings.append({'level': 'high', 'msg': f'成交量异常放大（{vol_ratio}x 均值），可能有重大消息'})
        elif vol_ratio < 0.3:
            warnings.append({'level': 'low', 'msg': f'成交量萎缩（{vol_ratio}x 均值），流动性不足'})

        # 3. 趋势风险
        trend = patterns.get('trend', {})
        if trend.get('overall') in ('弱势下跌',):
            warnings.append({'level': 'high', 'msg': '处于下跌趋势，抄底需谨慎'})

        # 4. 超买超卖风险
        rsi14 = indicators.get('rsi', {}).get('rsi14')
        if rsi14 is not None:
            if rsi14 > 80:
                warnings.append({'level': 'medium', 'msg': f'RSI严重超买（{rsi14}），回调风险大'})
            elif rsi14 < 20:
                warnings.append({'level': 'medium', 'msg': f'RSI严重超卖（{rsi14}），可能继续下跌'})

        # 5. 布林带位置
        boll = indicators.get('bollinger', {})
        latest_close = klines[-1].close
        if boll.get('upper') and latest_close > boll['upper']:
            warnings.append({'level': 'medium', 'msg': '价格突破布林上轨，短期可能回调'})
        elif boll.get('lower') and latest_close < boll['lower']:
            warnings.append({'level': 'medium', 'msg': '价格跌破布林下轨，短期可能反弹'})

        risk_level = 'low'
        if any(w['level'] == 'high' for w in warnings):
            risk_level = 'high'
        elif any(w['level'] == 'medium' for w in warnings):
            risk_level = 'medium'

        return {
            'level': risk_level,
            'warnings': warnings,
        }
