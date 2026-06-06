"""
闲鱼销售数据分析器
====================
功能：录入销售数据 → 自动计算关键指标 → 生成分析报告

使用方法：
  python sales_analyzer.py             # 交互式录入+分析
  python sales_analyzer.py --report    # 直接查看报告（不录入）
  python sales_analyzer.py --export    # 导出数据为CSV

数据文件：sales_data.json

作者：闲鱼二号店项目
日期：2026-06-06
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# 配置
# ============================================================

SCRIPT_DIR = Path(__file__).parent
DATA_FILE = SCRIPT_DIR / "sales_data.json"

MONTHLY_TARGET = 1000  # 月收入目标（元）

# 商品信息（与商品文案库保持一致）
PRODUCTS = {
    "P01": "DeepSeek保姆级教程",
    "P02": "AI编程助手Cursor指南",
    "P03": "Python自动化脚本合集",
    "P04": "AI绘画提示词大全",
    "P05": "Excel自动化宏合集",
    "P06": "文件批处理工具箱",
    "P07": "GitHub与VS Code指南",
    "P08": "数据分析Python脚本",
    "P09": "自媒体效率工具包",
    "P10": "程序员副业指南",
}


# ============================================================
# 数据管理
# ============================================================

def load_data():
    """加载销售数据"""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sales": []}


def save_data(data):
    """保存销售数据"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_sale():
    """录入一笔销售"""
    data = load_data()

    print("\n📝 录入新销售记录")
    print("-" * 40)

    # 选择商品
    print("商品列表:")
    for pid, name in PRODUCTS.items():
        print(f"  [{pid}] {name}")
    print(f"  [O]  其他/自定义")

    while True:
        pid = input("商品编号: ").strip().upper()
        if pid in PRODUCTS:
            name = PRODUCTS[pid]
            break
        elif pid == "O":
            name = input("商品名称: ").strip()
            pid = "OTHER"
            break
        else:
            print("⚠️  请输入有效编号")

    # 价格
    while True:
        try:
            price = float(input("售价（元）: ").strip())
            if price > 0:
                break
            print("⚠️  价格必须大于0")
        except ValueError:
            print("⚠️  请输入数字")

    # 日期（默认今天）
    date_str = input(f"日期（回车=今天 {datetime.now().strftime('%Y-%m-%d')}）: ").strip()
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 记录
    record = {
        "date": date_str,
        "product_id": pid,
        "product_name": name,
        "price": price,
    }
    data["sales"].append(record)
    save_data(data)

    print(f"✅ 已记录: {name} - {price}元 - {date_str}")
    return data


# ============================================================
# 分析功能
# ============================================================

def analyze(data):
    """分析销售数据"""
    sales = data.get("sales", [])

    if not sales:
        print("\n📊 暂无销售数据")
        print("   先录入数据: python sales_analyzer.py")
        return

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # 计算本月日期范围
    month_start = now.replace(day=1).strftime("%Y-%m-%d")

    # 筛选本月数据
    this_month_sales = [s for s in sales if s["date"] >= month_start]
    today_sales = [s for s in sales if s["date"] == today]

    # 基础统计
    total_month = len(this_month_sales)
    total_all = len(sales)
    revenue_month = sum(s["price"] for s in this_month_sales)
    revenue_all = sum(s["price"] for s in sales)
    revenue_today = sum(s["price"] for s in today_sales)

    # 本月天数
    days_passed = now.day
    daily_avg = revenue_month / days_passed if days_passed > 0 else 0

    # 按商品统计
    product_stats = {}
    for s in this_month_sales:
        pid = s["product_id"]
        if pid not in product_stats:
            product_stats[pid] = {"count": 0, "revenue": 0, "name": s["product_name"]}
        product_stats[pid]["count"] += 1
        product_stats[pid]["revenue"] += s["price"]

    # 按天统计趋势
    daily_trend = {}
    for s in this_month_sales:
        d = s["date"]
        if d not in daily_trend:
            daily_trend[d] = {"count": 0, "revenue": 0}
        daily_trend[d]["count"] += 1
        daily_trend[d]["revenue"] += s["price"]

    # ============================================================
    # 打印报告
    # ============================================================

    print("\n" + "=" * 60)
    print("📊 闲鱼二号店 · 销售分析报告")
    print("=" * 60)
    print(f"生成时间: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"统计范围: {month_start} ~ {today}")

    # 核心指标
    print(f"\n{'─'*40}")
    print("📈 核心指标")
    print(f"{'─'*40}")
    print(f"  📦 本月总单量: {total_month} 单")
    print(f"  💰 本月总收入: {revenue_month:.0f} 元")
    print(f"  📅 今日收入: {revenue_today:.0f} 元")
    print(f"  📊 日均收入: {daily_avg:.1f} 元/天")
    print(f"  📦 累计总单量: {total_all} 单")
    print(f"  💰 累计总收入: {revenue_all:.0f} 元")

    # 目标达成
    print(f"\n{'─'*40}")
    print("🎯 目标追踪")
    print(f"{'─'*40}")
    target_rate = revenue_month / MONTHLY_TARGET * 100
    days_remaining = 30 - days_passed if days_passed <= 30 else 0
    needed_daily = (MONTHLY_TARGET - revenue_month) / days_remaining if days_remaining > 0 else 0

    print(f"  月目标: {MONTHLY_TARGET} 元")
    print(f"  已完成: {revenue_month:.0f} 元 ({target_rate:.0f}%)")
    print(f"  剩余: {MONTHLY_TARGET - revenue_month:.0f} 元")
    print(f"  剩余天数: {days_remaining} 天")
    if needed_daily > 0:
        print(f"  需日均: {needed_daily:.1f} 元/天 才能达标")

    # 进度条
    bar_len = 30
    filled = int(bar_len * min(target_rate / 100, 1))
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"  [{bar}] {target_rate:.0f}%")

    # 状态判断
    if target_rate >= 100:
        print("\n  🎉 恭喜！已达成月度目标！")
    elif daily_avg >= 33:
        print(f"\n  ✅ 按当前日均{daily_avg:.0f}元，本月可完成目标")
    else:
        print(f"\n  ⚠️  当前日均{daily_avg:.0f}元，需提升至33元/天才能达标")

    # 商品排行榜
    if product_stats:
        print(f"\n{'─'*40}")
        print("🏆 本月商品排行榜")
        print(f"{'─'*40}")
        sorted_products = sorted(product_stats.items(), key=lambda x: x[1]["revenue"], reverse=True)
        print(f"  {'商品':<28} {'单量':>5} {'收入':>8}")
        print(f"  {'-'*42}")
        for pid, stats in sorted_products:
            bar = "█" * max(1, int(stats["revenue"] / max(1, revenue_month) * 15))
            print(f"  {stats['name']:<26} {stats['count']:>5}单 {stats['revenue']:>7.0f}元 {bar}")

    # 零销量商品
    sold_pids = set(product_stats.keys())
    all_pids = set(PRODUCTS.keys())
    zero_sales = all_pids - sold_pids
    if zero_sales:
        print(f"\n{'─'*40}")
        print("🔴 本月零销量商品（考虑优化或下架）")
        print(f"{'─'*40}")
        for pid in sorted(zero_sales):
            print(f"  ❌ [{pid}] {PRODUCTS[pid]}")

    # 趋势
    if len(daily_trend) >= 3:
        print(f"\n{'─'*40}")
        print("📈 日收入趋势（最近7天）")
        print(f"{'─'*40}")
        sorted_days = sorted(daily_trend.keys())[-7:]
        for day in sorted_days:
            d = daily_trend[day]
            bar = "█" * max(1, int(d["revenue"] / 10))
            print(f"  {day}  {d['revenue']:>6.0f}元 {bar}")

    print("\n" + "=" * 60)


def export_csv():
    """导出为CSV"""
    data = load_data()
    sales = data.get("sales", [])

    if not sales:
        print("暂无数据可导出")
        return

    csv_file = SCRIPT_DIR / f"sales_export_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(csv_file, "w", encoding="utf-8-sig") as f:
        f.write("日期,商品编号,商品名称,售价\n")
        for s in sales:
            f.write(f"{s['date']},{s['product_id']},{s['product_name']},{s['price']}\n")

    print(f"✅ 已导出: {csv_file}")


# ============================================================
# 主入口
# ============================================================

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║         闲鱼销售数据分析器 v1.0                          ║
║         Xianyu Sales Analyzer                            ║
╚══════════════════════════════════════════════════════════╝
    """)

    if "--report" in sys.argv or "-r" in sys.argv:
        data = load_data()
        analyze(data)
        return

    if "--export" in sys.argv or "-e" in sys.argv:
        export_csv()
        return

    # 交互模式
    data = load_data()

    while True:
        print("\n选项:")
        print("  [1] 录入销售记录")
        print("  [2] 查看分析报告")
        print("  [3] 导出CSV")
        print("  [Q] 退出")

        choice = input("\n选择: ").strip()

        if choice == "1":
            data = add_sale()
        elif choice == "2":
            analyze(data)
        elif choice == "3":
            export_csv()
        elif choice.upper() == "Q":
            print("👋 再见！")
            break
        else:
            print("⚠️  请输入 1/2/3/Q")


if __name__ == "__main__":
    main()
