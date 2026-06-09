"""输出格式化 — JSON 和终端表格输出"""

import json
import sys
from typing import Dict, Any


def _safe_emoji(text: str) -> str:
    """如果终端不支持Unicode emoji，替换为ASCII安全字符"""
    try:
        text.encode(sys.stdout.encoding or 'utf-8')
        return text
    except (UnicodeEncodeError, UnicodeError):
        pass
    # 替换emoji为ASCII替代
    replacements = {
        '📈': '[UP]', '📉': '[DN]', '📊': '[CHART]', '📐': '[MA]',
        '🔧': '[IND]', '📌': '[LVL]', '🟢': '[+]', '🔴': '[-]', '⚪': '[=]',
        '🕯️': '[PTN]', '🧠': '[STG]', '🔮': '[PRD]', '⚠️': '[!]',
        '💡': '[TIP]', '⏳': '[...]', '❌': '[X]', '📋': '[*]',
        '🎯': '[TGT]', '⏱️': '[TIME]', '📈': '[UP]', '📉': '[DN]',
    }
    for emoji, ascii_repl in replacements.items():
        text = text.replace(emoji, ascii_repl)
    return text


def format_json(report: Dict[str, Any], indent: int = 2) -> str:
    """将分析报告格式化为JSON字符串"""
    # 过滤掉不可序列化的KlineBar对象，只保留元数据
    clean = _clean_for_json(report)
    return json.dumps(clean, ensure_ascii=False, indent=indent)


def format_report(report: Dict[str, Any]) -> str:
    """将分析报告格式化为彩色终端输出"""
    meta = report['meta']
    summary = report['summary']
    indicators = report['indicators']
    risk = report['risk']

    lines = []
    # 分隔线
    W = 64

    # 标题
    stock_label = f"{meta.get('stock_name', '')} ({meta['code']})" if meta.get('stock_name') else meta['code']
    lines.append('=' * W)
    lines.append(f"  📈 {stock_label}  ·  {meta['period_label']}  ·  {meta['latest_time']}")
    lines.append('=' * W)

    # 价格
    price = meta['latest_price']
    change = meta.get('latest_change_pct', 0)
    direction = '🔴' if change > 0 else '🟢' if change < 0 else '⚪'
    lines.append(f"  最新价: ¥{price:.2f}  {direction} {change:+.2f}%")
    lines.append('')

    # 趋势
    trend = summary['trend']
    lines.append(f"  📊 趋势判断")
    lines.append(f"     综合评分: {summary['score']}/100 ({_bias_label(summary['bias'])})")
    lines.append(f"     整体趋势: {trend['overall']}")
    lines.append(f"     均线排列: {summary['ma_status']['arrangement']}")
    lines.append(f"     价格vs MA60: {trend.get('price_vs_ma60_pct', 0):+.2f}%")
    lines.append('')

    # 均线
    ma = summary['ma_status']
    lines.append(f"  📐 移动均线")
    lines.append(f"     MA5: {_v(ma['ma5'])}  MA10: {_v(ma['ma10'])}  MA20: {_v(ma['ma20'])}  MA60: {_v(ma['ma60'])}")
    lines.append('')

    # 技术指标
    lines.append(f"  🔧 技术指标")
    macd_s = summary['macd_status']
    rsi_s = summary['rsi_status']
    lines.append(f"     MACD: DIF={_v(macd_s['dif'])}  DEA={_v(macd_s['dea'])}  柱={_v(macd_s['histogram'])}")
    lines.append(f"     RSI: 6={_v(rsi_s['rsi6'])}  14={_v(rsi_s['rsi14'])}  24={_v(rsi_s['rsi24'])}  [{rsi_s['status']}]")

    boll = indicators.get('bollinger', {})
    lines.append(f"     布林: 上轨={_v(boll.get('upper'))}  中轨={_v(boll.get('middle'))}  下轨={_v(boll.get('lower'))}")

    kdj = indicators.get('kdj', {})
    lines.append(f"     KDJ: K={_v(kdj.get('k'))}  D={_v(kdj.get('d'))}  J={_v(kdj.get('j'))}")

    atr_pct = indicators.get('atr_pct')
    lines.append(f"     ATR: {_v(indicators.get('atr'))} ({_v(atr_pct)}%)")
    lines.append('')

    # 关键价位
    levels = summary['levels']
    lines.append(f"  📌 关键价位")
    lines.append(f"     最近支撑: {_v(levels['nearest_support'])}  (距离 {_vp(levels.get('dist_support_pct'))})")
    lines.append(f"     最近压力: {_v(levels['nearest_resistance'])}  (距离 {_vp(levels.get('dist_resistance_pct'))})")
    lines.append('')

    # 信号
    if summary['bullish_signals']:
        lines.append(f"  🟢 看多信号:")
        for s in summary['bullish_signals']:
            lines.append(f"     + {s}")
    if summary['bearish_signals']:
        lines.append(f"  🔴 看空信号:")
        for s in summary['bearish_signals']:
            lines.append(f"     - {s}")
    if not summary['bullish_signals'] and not summary['bearish_signals']:
        lines.append(f"  ⚪ 无明显方向信号")
    lines.append('')

    # 成交量
    vol = indicators.get('volume', {})
    lines.append(f"  📊 量价分析")
    lines.append(f"     POC（最大成交量价）: {vol.get('poc', 'N/A')}")
    lines.append(f"     价值区域: {vol.get('value_area', ('N/A', 'N/A'))}")
    lines.append(f"     量比: {vol.get('volume_ratio', 'N/A')}x  |  均量: {_vol(vol.get('avg_volume'))}")
    lines.append('')

    # 形态信号
    patterns = report.get('patterns', {})
    doji_n = patterns.get('doji_count', 0)
    hammer_n = patterns.get('hammer_count', 0)
    engulf_n = patterns.get('engulfing_count', 0)
    if doji_n or hammer_n or engulf_n:
        lines.append(f"  🕯️ K线形态 (历史检测)")
        lines.append(f"     十字星: {doji_n}次  锤子/倒锤: {hammer_n}次  吞没: {engulf_n}次")
    latest_signals = patterns.get('latest_signals', [])
    if latest_signals:
        lines.append(f"     最近5根K线信号:")
        for s in latest_signals[-5:]:
            emoji = '🟢' if s.get('signal') == 'bullish' else '🔴' if s.get('signal') == 'bearish' else '⚪'
            lines.append(f"       {emoji} {s.get('time','')} {s.get('name', s.get('doji_type', s.get('type','')))}")
    lines.append('')

    # 策略/预测结果（如果有注册）
    strategy_results = report.get('strategy_results', [])
    if strategy_results:
        lines.append(f"  🧠 策略分析 ({len(strategy_results)}个策略)")
        for sr in strategy_results:
            signals = sr.get('signals', [])
            lines.append(f"     [{sr['strategy']}] 置信度: {sr['confidence']:.0%}")
            for sig in signals:
                s_emoji = '📈' if sig['type'] == 'buy' else '📉' if sig['type'] == 'sell' else '➖'
                lines.append(f"       {s_emoji} {sig['type'].upper()} @{sig['price']} (强度{sig['strength']}) {sig['reason']}")
        lines.append('')

    prediction_results = report.get('prediction_results', [])
    if prediction_results:
        lines.append(f"  🔮 预测结果 ({len(prediction_results)}个预测器)")
        for pr in prediction_results:
            d_emoji = '📈' if pr['direction'] == 'up' else '📉' if pr['direction'] == 'down' else '➖'
            lines.append(f"     [{pr['predictor']}] {d_emoji} {pr['direction']} "
                         f"置信度{pr['confidence']:.0%}  周期{pr['horizon']}根K线")
            if pr.get('target_price'):
                lines.append(f"       目标价: ¥{pr['target_price']:.2f}")
            if pr.get('reason'):
                lines.append(f"       {pr['reason']}")
        lines.append('')

    # 风险
    lines.append(f"  ⚠️ 风险评估: {_risk_label(risk['level'])}")
    for w in risk.get('warnings', []):
        icon = '🔴' if w['level'] == 'high' else '🟡' if w['level'] == 'medium' else '🟢'
        lines.append(f"     {icon} {w['msg']}")
    lines.append('')

    # 加载状态
    if meta.get('strategies_loaded') == 0 and meta.get('predictors_loaded') == 0:
        lines.append(f"  💡 提示: 未加载策略/预测器。可通过 analyzer.strategies.register() 和")
        lines.append(f"     analyzer.predictors.register() 注册自定义策略和预测模型。")
        lines.append('')

    # 免责
    lines.append('─' * W)
    lines.append('  ⚠️ 以上分析仅供参考学习，不构成任何投资建议。')
    lines.append('─' * W)

    return _safe_emoji('\n'.join(lines))


def _v(val) -> str:
    """格式化单个数值"""
    if val is None:
        return '--'
    return f'{val:.2f}'


def _vp(val) -> str:
    """格式化百分比"""
    if val is None:
        return '--%'
    return f'{val:+.2f}%'


def _vol(val) -> str:
    """格式化成交量"""
    if val is None:
        return '--'
    if val >= 1e8:
        return f'{val/1e8:.1f}亿'
    if val >= 1e4:
        return f'{val/1e4:.0f}万'
    return f'{val:.0f}'


def _bias_label(bias: str) -> str:
    return {'bullish': '🟢 偏多', 'bearish': '🔴 偏空', 'neutral': '⚪ 中性'}.get(bias, bias)


def _risk_label(level: str) -> str:
    return {'low': '🟢 低风险', 'medium': '🟡 中等风险', 'high': '🔴 高风险'}.get(level, level)


def _clean_for_json(obj):
    """递归清洗对象，移除不可序列化的内容"""
    if isinstance(obj, dict):
        return {k: _clean_for_json(v) for k, v in obj.items()
                if not k.startswith('_')}
    elif isinstance(obj, list):
        return [_clean_for_json(v) for v in obj]
    elif hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj)
