"""
缠论引擎 — 完整分析流水线
分型 → 笔 → 线段 → 中枢 → 买卖点 → 多维度分析
"""
from .fractal import Fractal, process_containment, detect_fractals
from .stroke import Stroke, build_strokes, validate_stroke_alternation
from .segment import Segment, build_segments, detect_segment_divergence
from .center import Center, build_centers, analyze_center_gravity
from .buy_sell_point import BuySellPoint, detect_buy_sell_points, compute_macd
from .chan_analyzer import (
    ChanAnalyzer,
    ChanMultiDimResult,
    TurningPointDetail,
    AnomalyPoint,
    GlobalAnalysis,
    LocalAnalysis,
)
