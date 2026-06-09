#!/usr/bin/env python3
"""AI K线分析引擎 — CLI入口

使用方式:
    python main.py 000001              # 分析平安银行，默认日K
    python main.py 000001 day          # 指定周期
    python main.py 600519 week --json  # 分析贵州茅台周K，输出JSON
    python main.py 000001 day -n 300   # 获取300根K线

可用周期:
    5min, 15min, 30min, 60min, day, week, month
"""

import sys
import argparse
from core.data import KlineDataFetcher, PERIOD_MAP
from core.analyzer import KlineAnalyzer
from output.formatter import format_report, format_json, _safe_emoji

# Windows GBK终端强制使用UTF-8，避免emoji和特殊字符编码错误
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def main():
    parser = argparse.ArgumentParser(
        description='AI K线量化分析引擎',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python main.py 000001                    # 平安银行日K分析
  python main.py 600519 week --json        # 贵州茅台周K分析（JSON输出）
  python main.py 000001 60min -n 300       # 平安银行60分钟K线，300根
        ''',
    )
    parser.add_argument('code', nargs='?', default='000001',
                        help='股票代码（默认: 000001 平安银行）')
    parser.add_argument('period', nargs='?', default='day',
                        choices=list(PERIOD_MAP.keys()),
                        help='K线周期（默认: day）')
    parser.add_argument('-n', '--count', type=int, default=200,
                        help='获取K线条数（默认: 200）')
    parser.add_argument('--json', action='store_true',
                        help='以JSON格式输出（默认: 终端表格）')
    parser.add_argument('--no-cache', action='store_true',
                        help='不使用缓存，强制重新获取')

    args = parser.parse_args()

    # 初始化分析器
    analyzer = KlineAnalyzer()

    # 获取数据+分析
    try:
        if args.json:
            # JSON模式：先fetch再compute，分开输出
            report = analyzer.analyze(
                args.code, args.period, count=args.count,
            )
            print(format_json(report))
        else:
            print(_safe_emoji(f'\n⏳ 正在获取 {args.code} 的{args.period}K线数据...\n'))
            report = analyzer.analyze(
                args.code, args.period, count=args.count,
            )
            print(format_report(report))
    except Exception as e:
        print(_safe_emoji(f'\n❌ 分析失败: {e}'), file=sys.stderr)
        print(_safe_emoji(f'\n💡 提示:'), file=sys.stderr)
        print(_safe_emoji(f'   - 检查股票代码是否正确（如 000001, 600519）'), file=sys.stderr)
        print(_safe_emoji(f'   - 检查网络连接'), file=sys.stderr)
        print(_safe_emoji(f'   - 东方财富API可能需要几秒响应时间'), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
