#!/usr/bin/env python3
"""K线分析 API 服务器 — 为微信小程序提供后端分析能力

启动方式:
    python server.py                  # 默认 127.0.0.1:5000
    python server.py --port 8080      # 自定义端口
    python server.py --host 0.0.0.0   # 允许局域网访问（手机调试用）

小程序调用示例:
    wx.request({
        url: 'http://127.0.0.1:5000/api/analyze',
        method: 'POST',
        data: { code: '000001', period: 'day' },
        success: res => console.log(res.data)
    })
"""

import sys
import os
from flask import Flask, request, jsonify

# 确保能导入同目录的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.analyzer import KlineAnalyzer
from core.data import KlineBar
from output.formatter import format_report

app = Flask(__name__)

# 全局分析器实例（单例，策略/预测器只需注册一次）
analyzer = KlineAnalyzer()


# ============================================================
# API 路由
# ============================================================

@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'strategies': analyzer.strategies.list_all(),
        'predictors': analyzer.predictors.list_all(),
    })


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """K线综合分析

    Request JSON:
        { "code": "000001", "period": "day", "count": 200 }

    Response JSON:
        { "success": true, "data": { ... 完整分析报告 ... } }
    """
    data = request.get_json(silent=True) or {}
    code = str(data.get('code', '000001')).strip()
    period = str(data.get('period', 'day')).strip()
    count = int(data.get('count', 200))

    if not code:
        return jsonify({'success': False, 'error': '股票代码不能为空'}), 400

    valid_periods = ['5min', '15min', '30min', '60min', 'day', 'week', 'month']
    if period not in valid_periods:
        return jsonify({'success': False, 'error': f'无效周期: {period}'}), 400

    try:
        report = analyzer.analyze(code, period, count=count)
        return jsonify({'success': True, 'data': report})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze_data', methods=['POST'])
def analyze_data():
    """K线数据分析 — 接收小程序端已获取的K线数据（绕过Python→东方财富连接问题）

    Request JSON:
        {
            "code": "000001",
            "period": "day",
            "klines": [{ "time": "...", "open": 10.0, "close": 10.5, ... }, ...],
            "stock_name": "平安银行",
            "latest_price": 11.03,
            "latest_change_pct": 1.25
        }
    """
    data = request.get_json(silent=True) or {}
    code = str(data.get('code', '')).strip()
    period = str(data.get('period', 'day')).strip()
    klines_raw = data.get('klines', [])

    if not code:
        return jsonify({'success': False, 'error': '股票代码不能为空'}), 400
    if not klines_raw:
        return jsonify({'success': False, 'error': 'K线数据不能为空，请先获取K线数据'}), 400

    try:
        # 从JSON反序列化KlineBar列表
        klines = KlineBar.from_dict_array(klines_raw)

        # 使用分析器的内部方法直接分析
        indicators_data = analyzer.fetch_and_compute_data(klines, code, period)
        report = analyzer.analyze_from_data(klines, indicators_data, code, period,
                                            stock_name=data.get('stock_name', ''),
                                            latest_override={
                                                'price': data.get('latest_price'),
                                                'change_pct': data.get('latest_change_pct'),
                                            })
        return jsonify({'success': True, 'data': report})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analyze_simple', methods=['POST'])
def analyze_simple():
    """轻量分析 — 只返回摘要，适合列表页快速展示

    Request JSON:
        { "code": "000001", "period": "day" }
    """
    data = request.get_json(silent=True) or {}
    code = str(data.get('code', '000001')).strip()
    period = str(data.get('period', 'day')).strip()

    try:
        report = analyzer.analyze(code, period, count=200)
        return jsonify({
            'success': True,
            'data': {
                'code': report['meta']['code'],
                'name': report['meta']['stock_name'],
                'price': report['meta']['latest_price'],
                'change': report['meta']['latest_change_pct'],
                'trend': report['summary']['trend']['overall'],
                'score': report['summary']['score'],
                'bias': report['summary']['bias'],
                'risk': report['risk']['level'],
                'signals': {
                    'bullish': report['summary']['bullish_signals'],
                    'bearish': report['summary']['bearish_signals'],
                },
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/quote', methods=['POST'])
def quote():
    """实时行情快照

    Request JSON:
        { "code": "000001" }
    """
    data = request.get_json(silent=True) or {}
    code = str(data.get('code', '000001')).strip()

    # 直接复用 analyzer 的 fetcher
    try:
        klines = analyzer._fetcher.fetch_kline(code, 'day', 1)
        quote = analyzer._fetcher.fetch_quote(code)
        return jsonify({
            'success': True,
            'data': {
                'code': code,
                'name': quote.name,
                'price': quote.price,
                'change': quote.change,
                'change_pct': quote.change_pct,
                'high': quote.high,
                'low': quote.low,
                'volume': quote.volume,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search', methods=['POST'])
def search():
    """股票搜索

    Request JSON:
        { "keyword": "平安" }
    """
    data = request.get_json(silent=True) or {}
    keyword = str(data.get('keyword', '')).strip()

    if len(keyword) < 1:
        return jsonify({'success': False, 'error': '请输入搜索关键词'}), 400

    try:
        results = analyzer._fetcher.search(keyword)
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 策略/预测器管理 API
# ============================================================

@app.route('/api/strategies', methods=['GET'])
def list_strategies():
    """列出已注册的策略"""
    return jsonify({
        'success': True,
        'data': [
            {'name': s.name, 'description': s.description}
            for s in analyzer.strategies._strategies.values()
        ]
    })


@app.route('/api/predictors', methods=['GET'])
def list_predictors():
    """列出已注册的预测器"""
    return jsonify({
        'success': True,
        'data': [
            {'name': p.name, 'description': p.description}
            for p in analyzer.predictors._predictors.values()
        ]
    })


# ============================================================
# 启动入口
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='K线分析 API 服务器')
    parser.add_argument('--host', default='127.0.0.1', help='绑定地址 (默认: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000, help='端口 (默认: 5000)')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    args = parser.parse_args()

    print(f'''
╔══════════════════════════════════════════════════╗
║       K线量化分析引擎 — API 服务器                  ║
╠══════════════════════════════════════════════════╣
║  地址: http://{args.host}:{args.port}              ║
║  文档: POST /api/analyze  (综合分析)              ║
║        POST /api/analyze_data (K线数据分析，小程序直传)   ║
║        POST /api/quote      (实时行情)            ║
║        POST /api/search     (股票搜索)            ║
║        GET  /api/strategies (策略列表)            ║
║        GET  /api/predictors (预测器列表)           ║
║        GET  /api/health     (健康检查)            ║
╠══════════════════════════════════════════════════╣
║  已加载策略: {len(analyzer.strategies)}个                             ║
║  已加载预测器: {len(analyzer.predictors)}个                            ║
║  按 Ctrl+C 停止服务器                              ║
╚══════════════════════════════════════════════════╝
''')

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
