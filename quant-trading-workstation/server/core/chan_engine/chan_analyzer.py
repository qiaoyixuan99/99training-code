"""
缠论引擎 — 全局+局部多维度分析器
细化分析每一个拐点、每一个异常点，结合全局趋势和局部细节
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .fractal import Fractal, process_containment, detect_fractals
from .stroke import Stroke, build_strokes, validate_stroke_alternation
from .segment import Segment, build_segments, detect_segment_divergence
from .center import Center, build_centers, analyze_center_gravity
from .buy_sell_point import BuySellPoint, detect_buy_sell_points, compute_macd


@dataclass
class TurningPointDetail:
    """拐点详细分析"""
    index: int
    date: str
    type: str               # 'top' | 'bottom'
    price: float
    # 局部特征
    local_high: float       # 局部N日最高
    local_low: float        # 局部N日最低
    local_range_pct: float  # 局部振幅百分比
    volume_ratio: float     # 当日量/5日均量
    # 趋势特征
    trend_position: str     # 'leading'|'lagging'|'reversal'
    trend_strength: float   # 趋势强度
    # 异常标记
    anomalies: List[str] = field(default_factory=list)
    # 拐点级别
    level: str = 'minor'    # 'major'|'medium'|'minor'


@dataclass
class AnomalyPoint:
    """异常点分析"""
    index: int
    date: str
    type: str               # 'volume_spike'|'price_gap'|'divergence'|'false_break'|'abnormal_range'
    description: str
    severity: str           # 'high'|'medium'|'low'
    related_points: List[int] = field(default_factory=list)


@dataclass
class GlobalAnalysis:
    """全局趋势分析"""
    trend: str              # 'bullish'|'bearish'|'ranging'
    trend_strength: float   # 0-100
    phase: str              # 'accumulation'|'uptrend'|'distribution'|'downtrend'
    # 多周期共振
    multi_period_resonance: str = 'none'  # 'resonant_up'|'resonant_down'|'divergent'
    # 关键位
    key_support: float = 0
    key_resistance: float = 0
    # 市场结构
    structure_health: float = 50  # 0-100 结构健康度
    # 总结
    summary: str = ''


@dataclass
class LocalAnalysis:
    """局部分析"""
    current_trend: str         # 当前局部趋势
    nearest_fractal: Optional[Dict] = None
    nearest_center: Optional[Dict] = None
    pending_signals: List[str] = field(default_factory=list)
    risk_level: str = 'medium'  # 'high'|'medium'|'low'


@dataclass
class ChanMultiDimResult:
    """多维度缠论分析结果"""
    symbol: str
    period: str
    data_points: int
    date_range: Tuple[str, str]

    # 基础数据
    fractals: List[Dict]
    strokes: List[Dict]
    segments: List[Dict]
    centers: List[Dict]
    buy_points: List[Dict]
    sell_points: List[Dict]

    # 全局分析
    global_analysis: Dict

    # 局部分析
    local_analysis: Dict

    # 拐点详细分析
    turning_points: List[Dict]

    # 异常点
    anomalies: List[Dict]

    # 汇总信号
    signals: List[Dict]


class ChanAnalyzer:
    """缠论多维度分析器"""

    def __init__(self, df: pd.DataFrame, symbol: str = '', period: str = '1d'):
        self.df = df
        self.symbol = symbol
        self.period = period
        self._df_contained: Optional[pd.DataFrame] = None
        self._fractals: List[Fractal] = []
        self._strokes: List[Stroke] = []
        self._segments: List[Segment] = []
        self._centers: List[Center] = []
        self._buy_points: List[BuySellPoint] = []
        self._sell_points: List[BuySellPoint] = []
        self._df_macd: Optional[pd.DataFrame] = None

    def _get_min_kline_count(self) -> int:
        """根据周期返回笔的最小K线数"""
        config = {
            '5m': 5, '15m': 5, '30m': 5, '60m': 5, '1m': 5,
            '1d': 4, 'daily': 4,
            '1w': 3, 'weekly': 3,
            '1M': 2, 'monthly': 2,
            '1Y': 1, 'yearly': 1,
        }
        return config.get(self.period, 5)

    def run_full_analysis(self) -> ChanMultiDimResult:
        """执行完整分析流程"""
        # 1. 包含处理（用于辅助分型识别）并对齐到原始K线
        self._df_contained = process_containment(self.df)

        # 2. 顶底分型 — 在原始K线上检测（避免索引映射问题）
        self._fractals = detect_fractals(self.df)

        # 3. 笔 — 不同周期使用不同的最小K线数
        min_k = self._get_min_kline_count()
        self._strokes = build_strokes(self._fractals, self.df, min_kline_count=min_k)
        self._strokes = validate_stroke_alternation(self._strokes)

        # 4. 线段
        self._segments = build_segments(self._strokes, self.df)

        # 5. 中枢
        self._centers = build_centers(
            self._segments, self._strokes, self.df, self.period
        )

        # 6. 买卖点
        self._df_macd = compute_macd(self.df)
        self._buy_points, self._sell_points = detect_buy_sell_points(
            self.df, self._fractals, self._strokes,
            self._segments, self._centers,
        )

        # 7. 全局分析
        global_analysis = self._global_analysis()

        # 8. 局部分析
        local_analysis = self._local_analysis()

        # 9. 拐点详细分析
        turning_points = self._analyze_turning_points()

        # 10. 异常检测
        anomalies = self._detect_anomalies()

        # 11. 信号汇总
        signals = self._aggregate_signals()

        date_start = str(self.df.index[0])[:10]
        date_end = str(self.df.index[-1])[:10]

        return ChanMultiDimResult(
            symbol=self.symbol,
            period=self.period,
            data_points=len(self.df),
            date_range=(date_start, date_end),

            fractals=[self._fractal_to_dict(f) for f in self._fractals],
            strokes=[self._stroke_to_dict(s) for s in self._strokes],
            segments=[self._segment_to_dict(s) for s in self._segments],
            centers=[self._center_to_dict(c) for c in self._centers],
            buy_points=[self._bsp_to_dict(p) for p in self._buy_points],
            sell_points=[self._bsp_to_dict(p) for p in self._sell_points],

            global_analysis=global_analysis,
            local_analysis=local_analysis,
            turning_points=turning_points,
            anomalies=anomalies,
            signals=signals,
        )

    # ── 全局分析 ────────────────────────────

    def _global_analysis(self) -> Dict:
        """全局多维度趋势分析"""
        close = self.df['close'].values
        high = self.df['high'].values
        low = self.df['low'].values

        # 趋势判断：基于MA排列
        ma5 = _calc_sma(close, 5)
        ma20 = _calc_sma(close, 20)
        ma60 = _calc_sma(close, 60)

        # 均线多头/空头排列
        if len(ma5) > 0 and len(ma20) > 0 and len(ma60) > 0:
            last_ma5, last_ma20, last_ma60 = ma5[-1], ma20[-1], ma60[-1]
            if last_ma5 > last_ma20 > last_ma60:
                trend = 'bullish'
                trend_score = 75
            elif last_ma5 < last_ma20 < last_ma60:
                trend = 'bearish'
                trend_score = 25
            else:
                trend = 'ranging'
                trend_score = 50
        else:
            trend = 'unknown'
            trend_score = 50

        # 市场阶段判断
        phase = self._identify_phase(close, high, low)

        # 关键支撑/阻力（基于中枢）
        current_price = close[-1]
        gravity = analyze_center_gravity(self._centers, current_price)
        key_support = gravity['nearest_support'] or _find_recent_low(low, 20)
        key_resistance = gravity['nearest_resistance'] or _find_recent_high(high, 20)

        # 线段背驰检测
        seg_divs = detect_segment_divergence(self._segments)
        has_divergence = len(seg_divs) > 0

        # 结构健康度
        structure_health = self._evaluate_structure_health()

        # 多周期共振（基于本周期内部结构）
        resonance = 'none'
        if trend == 'bullish' and gravity['position'] == 'above_all':
            resonance = 'resonant_up'
        elif trend == 'bearish' and gravity['position'] == 'below_all':
            resonance = 'resonant_down'
        elif trend == 'ranging' and gravity['inside_center']:
            resonance = 'consolidating'

        # 生成总结
        summary_parts = []
        summary_parts.append(f"整体趋势：{'上涨' if trend == 'bullish' else '下跌' if trend == 'bearish' else '震荡'}")
        summary_parts.append(f"所处阶段：{phase}")
        summary_parts.append(f"识别{len(self._fractals)}个分型，{len(self._strokes)}笔，{len(self._segments)}段，{len(self._centers)}个中枢")
        summary_parts.append(f"发现{len(self._buy_points)}个买点，{len(self._sell_points)}个卖点")
        if has_divergence:
            summary_parts.append(f"存在线段级别背驰，需要关注反转风险")
        if gravity['inside_center']:
            summary_parts.append("当前价格处于中枢区间内，方向不明确")
        summary_parts.append(f"结构健康度：{structure_health:.0f}/100")

        return {
            'trend': trend,
            'trend_strength': trend_score,
            'phase': phase,
            'multi_period_resonance': resonance,
            'key_support': round(key_support, 2),
            'key_resistance': round(key_resistance, 2),
            'structure_health': round(structure_health, 1),
            'has_segment_divergence': has_divergence,
            'segment_divergences': seg_divs,
            'center_gravity': gravity,
            'fractal_count': len(self._fractals),
            'stroke_count': len(self._strokes),
            'segment_count': len(self._segments),
            'center_count': len(self._centers),
            'summary': '；'.join(summary_parts),
        }

    def _identify_phase(self, close, high, low) -> str:
        """识别市场阶段"""
        if len(close) < 120:
            return 'insufficient_data'

        # 分为四段比较
        quarters = np.array_split(close, 4)
        q_means = [q.mean() for q in quarters]

        if q_means[0] > q_means[1] > q_means[2] > q_means[3]:
            return 'downtrend'
        elif q_means[0] < q_means[1] < q_means[2] < q_means[3]:
            return 'uptrend'
        elif q_means[0] < q_means[1] and q_means[2] > q_means[3] and q_means[0] < q_means[3]:
            return 'distribution'  # 先涨后跌，顶部派发
        elif q_means[0] > q_means[1] and q_means[2] < q_means[3] and q_means[0] > q_means[3]:
            return 'accumulation'  # 先跌后涨，底部吸筹
        else:
            return 'ranging'

    def _evaluate_structure_health(self) -> float:
        """评估市场结构健康度（0-100）"""
        score = 50.0

        # 分型质量：顶底交替的规整度
        if len(self._fractals) >= 4:
            alternation_ok = all(
                self._fractals[i].type != self._fractals[i + 1].type
                for i in range(len(self._fractals) - 1)
            )
            score += 15 if alternation_ok else -10

        # 笔的力度均匀性
        if len(self._strokes) >= 3:
            strengths = [s.strength for s in self._strokes]
            std_strength = np.std(strengths) if len(strengths) > 1 else 0
            if std_strength < 5:
                score += 10  # 力度均匀
            elif std_strength < 15:
                score += 5
            else:
                score -= 5  # 力度不均，结构不稳定

        # 中枢质量
        if self._centers:
            avg_strength = np.mean([c.strength for c in self._centers])
            score += min(avg_strength, 15)  # 最多+15

        # 买卖点置信度
        all_points = self._buy_points + self._sell_points
        if all_points:
            avg_conf = np.mean([p.confidence for p in all_points])
            score += avg_conf * 10  # 最多+10

        return max(0, min(100, score))

    # ── 局部分析 ────────────────────────────

    def _local_analysis(self) -> Dict:
        """当前局部位置分析"""
        current_price = self.df['close'].iloc[-1]
        current_idx = len(self.df) - 1

        # 最近分型
        nearest_fractal = None
        nearest_dist = float('inf')
        for f in self._fractals:
            dist = abs(f.index - current_idx)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_fractal = {
                    'index': f.index,
                    'date': str(f.date)[:10],
                    'type': f.type,
                    'price': round(f.high if f.type == 'top' else f.low, 2),
                    'distance': dist,
                    'position': 'above' if (f.type == 'top' and f.high > current_price) or
                                           (f.type == 'bottom' and f.low > current_price)
                    else 'below',
                }

        # 最近中枢
        nearest_center = None
        nearest_c_dist = float('inf')
        for c in self._centers:
            dist = abs(c.end_index - current_idx)
            if dist < nearest_c_dist:
                nearest_c_dist = dist
                nearest_center = self._center_to_dict(c)

        # 当前局部趋势（最近N根K线）
        n = min(20, len(self.df))
        recent = self.df.iloc[-n:]
        local_trend = 'up' if recent['close'].iloc[-1] > recent['close'].iloc[0] else 'down'

        # 待确认信号
        pending = []
        if nearest_fractal and nearest_fractal['type'] == 'top' and local_trend == 'down':
            pending.append('顶分型确认下行，关注下方支撑')
        if nearest_fractal and nearest_fractal['type'] == 'bottom' and local_trend == 'up':
            pending.append('底分型确认上行，关注上方阻力')
        if nearest_center and nearest_center['zd'] <= current_price <= nearest_center['zg']:
            pending.append('价格在中枢内运行，等待突破方向')

        # 风险等级
        risk = self._assess_local_risk(current_price, current_idx)

        return {
            'current_trend': local_trend,
            'current_price': round(current_price, 2),
            'nearest_fractal': nearest_fractal,
            'nearest_center': nearest_center,
            'pending_signals': pending,
            'risk_level': risk,
            'distance_to_support': round(current_price - (nearest_center['zd'] if nearest_center else current_price), 2),
            'distance_to_resistance': round((nearest_center['zg'] if nearest_center else current_price) - current_price, 2),
        }

    def _assess_local_risk(self, price: float, idx: int) -> str:
        """评估局部风险等级"""
        risks = 0

        # 处于中枢内部 = 低风险（有明确支撑阻力）
        inside_center = any(c.zd <= price <= c.zg for c in self._centers)
        if inside_center:
            risks -= 1
        else:
            risks += 1  # 离开中枢 = 趋势延续但方向风险

        # 接近支撑/阻力
        if self._centers:
            gravity = analyze_center_gravity(self._centers, price)
            if gravity['nearest_resistance'] and price > gravity['nearest_resistance'] * 0.95:
                risks += 1  # 接近阻力
            if gravity['nearest_support'] and price < gravity['nearest_support'] * 1.05:
                risks -= 0  # 接近支撑是有利的

        # 近期有无背驰
        recent_div = False
        for seg_div in detect_segment_divergence(self._segments):
            seg_idx = seg_div['segment_idx']
            if seg_idx < len(self._segments) and self._segments[seg_idx].end_index >= idx - 20:
                recent_div = True
                break
        if recent_div:
            risks += 2

        if risks <= -1:
            return 'low'
        elif risks >= 2:
            return 'high'
        return 'medium'

    # ── 拐点分析 ────────────────────────────

    def _analyze_turning_points(self) -> List[Dict]:
        """细化分析每一个拐点"""
        results = []

        for f in self._fractals:
            idx = f.index
            tp = self._analyze_single_turning_point(f)
            results.append(tp)

        return results

    def _analyze_single_turning_point(self, f: Fractal) -> Dict:
        """分析单个拐点"""
        idx = f.index
        price = f.high if f.type == 'top' else f.low

        # 局部范围（前后各5根K线）
        start = max(0, idx - 5)
        end = min(len(self.df) - 1, idx + 5)
        local_df = self.df.iloc[start:end + 1]
        local_high = local_df['high'].max()
        local_low = local_df['low'].min()
        local_range = (local_high - local_low) / local_low * 100 if local_low > 0 else 0

        # 量比
        vol = self.df['volume'].iloc[idx]
        vol_start = max(0, idx - 5)
        avg_vol = self.df['volume'].iloc[vol_start:idx].mean() if idx > vol_start else vol
        vol_ratio = vol / avg_vol if avg_vol > 0 else 1

        # 趋势位置
        trend_pos = self._determine_trend_position(f)

        # 拐点级别
        level = self._determine_fractal_level(f)

        # 异常检测
        anomalies = []
        if vol_ratio > 2.5:
            anomalies.append(f"放量{vol_ratio:.1f}倍，异常放量{ '见顶' if f.type == 'top' else '见底'}信号")
        if local_range > 10:
            anomalies.append(f"局部振幅{local_range:.1f}%，剧烈波动")

        # 检查是否为假突破
        if f.type == 'top':
            # 顶分型后是否快速回落
            next_n = min(idx + 3, len(self.df) - 1)
            if next_n > idx and self.df['close'].iloc[next_n] < price * 0.97:
                anomalies.append("顶分型后3日快速回落>3%，确认有效")
        else:
            next_n = min(idx + 3, len(self.df) - 1)
            if next_n > idx and self.df['close'].iloc[next_n] > price * 1.03:
                anomalies.append("底分型后3日快速反弹>3%，确认有效")

        # 检查是否构成笔的端点
        is_stroke_endpoint = any(
            s.start_index == idx or s.end_index == idx for s in self._strokes
        )
        is_segment_endpoint = any(
            s.start_index == idx or s.end_index == idx for s in self._segments
        )

        return {
            'index': idx,
            'date': str(f.date)[:10],
            'type': f.type,
            'price': round(price, 2),
            'local_high': round(local_high, 2),
            'local_low': round(local_low, 2),
            'local_range_pct': round(local_range, 2),
            'volume_ratio': round(vol_ratio, 2),
            'trend_position': trend_pos,
            'level': level,
            'is_stroke_endpoint': is_stroke_endpoint,
            'is_segment_endpoint': is_segment_endpoint,
            'anomalies': anomalies,
        }

    def _determine_trend_position(self, f: Fractal) -> str:
        """判断拐点在趋势中的位置"""
        close = self.df['close'].values
        idx = f.index

        if idx < 20:
            return 'leading' if idx < 10 else 'normal'

        # 比较前后趋势
        pre_ma = np.mean(close[idx - 20:idx])
        if idx + 10 < len(close):
            post_ma = np.mean(close[idx:idx + 10])
        else:
            post_ma = np.mean(close[idx:])
        post_ma = np.mean(close[idx:min(idx + 10, len(close))])

        if f.type == 'top':
            if pre_ma < post_ma and close[idx] > pre_ma * 1.1:
                return 'leading'  # 领涨后的顶部
            elif pre_ma > post_ma:
                return 'reversal'  # 反转顶部
        else:
            if pre_ma > post_ma and close[idx] < pre_ma * 0.9:
                return 'leading'  # 领跌后的底部
            elif pre_ma < post_ma:
                return 'reversal'  # 反转底部

        return 'normal'

    def _determine_fractal_level(self, f: Fractal) -> str:
        """判断分型级别"""
        # 构成线段端点的分型 = 主要 (major)
        # 构成笔端点的分型 = 中等 (medium)
        # 其他 = 次要 (minor)

        is_seg_end = any(
            s.start_index == f.index or s.end_index == f.index
            for s in self._segments
        )
        is_stroke_end = any(
            s.start_index == f.index or s.end_index == f.index
            for s in self._strokes
        )

        if is_seg_end:
            return 'major'
        elif is_stroke_end:
            return 'medium'
        return 'minor'

    # ── 异常检测 ────────────────────────────

    def _detect_anomalies(self) -> List[Dict]:
        """检测所有异常点"""
        anomalies = []

        # 1. 量能异常
        anomalies.extend(self._detect_volume_anomalies())

        # 2. 价格缺口
        anomalies.extend(self._detect_price_gaps())

        # 3. 背驰异常
        anomalies.extend(self._detect_divergence_anomalies())

        # 4. 假突破
        anomalies.extend(self._detect_false_breakouts())

        # 5. 异常振幅
        anomalies.extend(self._detect_abnormal_ranges())

        # 按严重程度排序
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        anomalies.sort(key=lambda x: (severity_order.get(x['severity'], 2), x['index']))

        return anomalies

    def _detect_volume_anomalies(self) -> List[Dict]:
        """量能异常检测"""
        anomalies = []
        volume = self.df['volume'].values

        # 计算20日均量
        avg_vol_20 = _calc_sma(volume.astype(float), 20)

        for i in range(20, len(volume)):
            if avg_vol_20[i - 1] > 0:
                ratio = volume[i] / avg_vol_20[i - 1]

                if ratio > 3.0:
                    # 巨量
                    is_up = self.df['close'].iloc[i] > self.df['open'].iloc[i]
                    anomalies.append({
                        'index': i,
                        'date': str(self.df.index[i])[:10],
                        'type': 'volume_spike',
                        'description': f"{'放量上涨' if is_up else '放量下跌'}，量比{ratio:.1f}倍，" +
                                      f"{'主力出货嫌疑' if not is_up else '主力进场或对倒'}",
                        'severity': 'high' if ratio > 5 else 'medium',
                    })
                elif ratio < 0.3 and i > 0:
                    anomalies.append({
                        'index': i,
                        'date': str(self.df.index[i])[:10],
                        'type': 'volume_spike',
                        'description': f"极度缩量，量比{ratio:.2f}倍，交投清淡，变盘前兆",
                        'severity': 'medium',
                    })

        return anomalies[:20]  # 限制数量

    def _detect_price_gaps(self) -> List[Dict]:
        """价格缺口检测"""
        anomalies = []

        for i in range(1, len(self.df)):
            prev_high = self.df['high'].iloc[i - 1]
            prev_low = self.df['low'].iloc[i - 1]
            curr_open = self.df['open'].iloc[i]
            prev_close = self.df['close'].iloc[i - 1]

            # 向上跳空
            if curr_open > prev_high * 1.01:
                gap_pct = (curr_open - prev_high) / prev_high * 100
                # 检查后续是否回补
                filled = any(
                    self.df['low'].iloc[j] <= prev_high
                    for j in range(i, min(i + 5, len(self.df)))
                )
                anomalies.append({
                    'index': i,
                    'date': str(self.df.index[i])[:10],
                    'type': 'price_gap',
                    'description': f"向上跳空开盘，缺口{gap_pct:.1f}%，" +
                                  ('已回补' if filled else '未回补，强势特征'),
                    'severity': 'high' if not filled else 'medium',
                })

            # 向下跳空
            if curr_open < prev_low * 0.99:
                gap_pct = (prev_low - curr_open) / prev_low * 100
                filled = any(
                    self.df['high'].iloc[j] >= prev_low
                    for j in range(i, min(i + 5, len(self.df)))
                )
                anomalies.append({
                    'index': i,
                    'date': str(self.df.index[i])[:10],
                    'type': 'price_gap',
                    'description': f"向下跳空开盘，缺口{gap_pct:.1f}%，" +
                                  ('已回补' if filled else '未回补，弱势特征'),
                    'severity': 'high' if not filled else 'medium',
                })

        return anomalies[:20]

    def _detect_divergence_anomalies(self) -> List[Dict]:
        """背驰异常检测"""
        anomalies = []

        if self._df_macd is None:
            return anomalies

        # 对每个底分型检测底背驰
        bottom_fractals = [f for f in self._fractals if f.type == 'bottom']
        for i in range(1, len(bottom_fractals)):
            curr = bottom_fractals[i]
            prev = bottom_fractals[i - 1]

            curr_price = curr.low
            prev_price = prev.low

            if curr_price < prev_price:  # 价格创新低
                curr_dif = _safe_get(self._df_macd, curr.index, 'dif')
                prev_dif = _safe_get(self._df_macd, prev.index, 'dif')

                if curr_dif is not None and prev_dif is not None and curr_dif > prev_dif:
                    anomalies.append({
                        'index': curr.index,
                        'date': str(curr.date)[:10],
                        'type': 'divergence',
                        'description': f"底背驰：价格{curr_price:.2f}低于前低{prev_price:.2f}，" +
                                      f"但DIF{curr_dif:.4f}高于前值{prev_dif:.4f}",
                        'severity': 'high',
                    })

        # 对每个顶分型检测顶背驰
        top_fractals = [f for f in self._fractals if f.type == 'top']
        for i in range(1, len(top_fractals)):
            curr = top_fractals[i]
            prev = top_fractals[i - 1]

            curr_price = curr.high
            prev_price = prev.high

            if curr_price > prev_price:  # 价格创新高
                curr_dif = _safe_get(self._df_macd, curr.index, 'dif')
                prev_dif = _safe_get(self._df_macd, prev.index, 'dif')

                if curr_dif is not None and prev_dif is not None and curr_dif < prev_dif:
                    anomalies.append({
                        'index': curr.index,
                        'date': str(curr.date)[:10],
                        'type': 'divergence',
                        'description': f"顶背驰：价格{curr_price:.2f}高于前高{prev_price:.2f}，" +
                                      f"但DIF{curr_dif:.4f}低于前值{prev_dif:.4f}",
                        'severity': 'high',
                    })

        return anomalies

    def _detect_false_breakouts(self) -> List[Dict]:
        """假突破检测"""
        anomalies = []

        for c in self._centers:
            zg, zd = c.zg, c.zd

            # 检查是否有K线突破ZG后回落（假突破上轨）
            for i in range(c.start_index, min(c.end_index + 10, len(self.df))):
                if self.df['high'].iloc[i] > zg * 1.02:
                    # 突破上轨
                    close_i = self.df['close'].iloc[i]
                    if close_i < zg:  # 收盘回落
                        anomalies.append({
                            'index': i,
                            'date': str(self.df.index[i])[:10],
                            'type': 'false_break',
                            'description': f"假突破：盘中突破中枢上轨{zg:.2f}，但收盘{close_i:.2f}回落至中枢内",
                            'severity': 'high',
                        })
                        break

            # 检查是否有K线跌破ZD后拉回（假跌破下轨）
            for i in range(c.start_index, min(c.end_index + 10, len(self.df))):
                if self.df['low'].iloc[i] < zd * 0.98:
                    close_i = self.df['close'].iloc[i]
                    if close_i > zd:  # 收盘拉回
                        anomalies.append({
                            'index': i,
                            'date': str(self.df.index[i])[:10],
                            'type': 'false_break',
                            'description': f"假跌破：盘中跌破中枢下轨{zd:.2f}，但收盘{close_i:.2f}拉回中枢内",
                            'severity': 'high',
                        })
                        break

        return anomalies

    def _detect_abnormal_ranges(self) -> List[Dict]:
        """异常振幅检测"""
        anomalies = []
        n = len(self.df)

        for i in range(1, n):
            o, h, l, c = (
                self.df['open'].iloc[i],
                self.df['high'].iloc[i],
                self.df['low'].iloc[i],
                self.df['close'].iloc[i],
            )
            if o > 0:
                range_pct = (h - l) / o * 100
                if range_pct > 8:  # 振幅超8%
                    real_body = abs(c - o) / o * 100
                    anomalies.append({
                        'index': i,
                        'date': str(self.df.index[i])[:10],
                        'type': 'abnormal_range',
                        'description': f"异常振幅{range_pct:.1f}%，实体{real_body:.1f}%，" +
                                      ('长阳线，强势突破' if c > o else '长阴线，恐慌抛售'),
                        'severity': 'high' if range_pct > 12 else 'medium',
                    })

        return anomalies[:15]

    # ── 信号汇总 ────────────────────────────

    def _aggregate_signals(self) -> List[Dict]:
        """汇总所有交易信号"""
        signals = []

        # 买卖点信号
        for bp in self._buy_points:
            signals.append({
                'index': bp.index,
                'date': str(bp.date)[:10],
                'direction': 'buy',
                'type': bp.type,
                'price': bp.price,
                'description': bp.description,
                'confidence': bp.confidence,
                'source': 'chan_theory',
            })

        for sp in self._sell_points:
            signals.append({
                'index': sp.index,
                'date': str(sp.date)[:10],
                'direction': 'sell',
                'type': sp.type,
                'price': sp.price,
                'description': sp.description,
                'confidence': sp.confidence,
                'source': 'chan_theory',
            })

        # 背驰信号（从异常点中提取）
        for anom in self._detect_divergence_anomalies():
            signals.append({
                'index': anom['index'],
                'date': anom['date'],
                'direction': 'buy' if '底背驰' in anom['description'] else 'sell',
                'type': 'divergence',
                'price': 0,  # 背驰不指定精确价格
                'description': anom['description'],
                'confidence': 0.8,
                'source': 'divergence_detection',
            })

        # 按日期排序
        signals.sort(key=lambda x: x['index'])

        return signals

    # ── 序列化辅助 ──────────────────────────

    def _fractal_to_dict(self, f: Fractal) -> Dict:
        return {
            'index': f.index,
            'date': str(f.date)[:10],
            'type': f.type,
            'high': round(f.high, 2),
            'low': round(f.low, 2),
        }

    def _stroke_to_dict(self, s: Stroke) -> Dict:
        return {
            'start_index': s.start_index,
            'end_index': s.end_index,
            'start_date': str(s.start_date)[:10],
            'end_date': str(s.end_date)[:10],
            'direction': s.direction,
            'start_price': round(s.start_price, 2),
            'end_price': round(s.end_price, 2),
            'high': round(s.high, 2),
            'low': round(s.low, 2),
            'kline_count': s.kline_count,
            'strength': s.strength,
        }

    def _segment_to_dict(self, s: Segment) -> Dict:
        return {
            'start_index': s.start_index,
            'end_index': s.end_index,
            'start_date': str(s.start_date)[:10],
            'end_date': str(s.end_date)[:10],
            'direction': s.direction,
            'start_price': round(s.start_price, 2),
            'end_price': round(s.end_price, 2),
            'high': round(s.high, 2),
            'low': round(s.low, 2),
            'stroke_count': s.stroke_count,
            'strength': s.strength,
            'strokes': s.strokes,
        }

    def _center_to_dict(self, c: Center) -> Dict:
        return {
            'zg': c.zg,
            'zd': c.zd,
            'zz': c.zz,
            'start_index': c.start_index,
            'end_index': c.end_index,
            'start_date': str(c.start_date)[:10],
            'end_date': str(c.end_date)[:10],
            'level': c.level,
            'strength': c.strength,
            'kline_count': c.kline_count,
            'segments': c.segments,
        }

    def _bsp_to_dict(self, p: BuySellPoint) -> Dict:
        return {
            'index': p.index,
            'date': str(p.date)[:10],
            'type': p.type,
            'price': round(p.price, 2),
            'description': p.description,
            'confidence': round(p.confidence, 2),
            'divergence_type': p.divergence_type,
        }


# ── 工具函数 ────────────────────────────────

def _calc_sma(data: np.ndarray, period: int) -> np.ndarray:
    """简单移动平均"""
    result = np.full_like(data, np.nan, dtype=float)
    for i in range(period - 1, len(data)):
        result[i] = np.mean(data[i - period + 1:i + 1])
    return result


def _find_recent_high(high: np.ndarray, n: int) -> float:
    return float(np.max(high[-n:])) if len(high) >= n else float(np.max(high))


def _find_recent_low(low: np.ndarray, n: int) -> float:
    return float(np.min(low[-n:])) if len(low) >= n else float(np.min(low))


def _safe_get(df: pd.DataFrame, idx: int, col: str) -> Optional[float]:
    if 0 <= idx < len(df):
        val = df[col].iloc[idx]
        if not np.isnan(val) and not np.isinf(val):
            return float(val)
    return None
