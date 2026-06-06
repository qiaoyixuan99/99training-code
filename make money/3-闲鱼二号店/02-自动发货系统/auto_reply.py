"""
闲鱼自动发货辅助系统
======================
功能：
  1. 交互模式    —— 选择商品 → 生成回复文案（含网盘链接）
  2. 链接检查模式 —— 批量检查网盘链接是否有效
  3. 统计模式    —— 查看发货记录和销售统计

使用方法：
  python auto_reply.py              # 交互模式
  python auto_reply.py --check      # 链接检查模式
  python auto_reply.py --stats      # 统计模式

作者：闲鱼二号店项目
日期：2026-06-06
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置区 —— 修改这里的网盘链接和提取码
# ============================================================

# 为每个商品设置网盘链接和提取码
# 替换下面的 "你的网盘链接" 和 "提取码" 为实际值
PRODUCT_CONFIG = {
    "P01": {
        "link": "https://pan.baidu.com/s/xxxxxxxxx",
        "code": "abcd",
    },
    "P02": {
        "link": "https://pan.baidu.com/s/xxxxxxxxx",
        "code": "abcd",
    },
    "P03": {
        "link": "https://pan.baidu.com/s/xxxxxxxxx",
        "code": "abcd",
    },
    "P04": {
        "link": "https://pan.baidu.com/s/xxxxxxxxx",
        "code": "abcd",
    },
    "P05": {
        "link": "https://pan.baidu.com/s/xxxxxxxxx",
        "code": "abcd",
    },
    "P06": {
        "link": "https://pan.baidu.com/s/xxxxxxxxx",
        "code": "abcd",
    },
    "P07": {
        "link": "https://pan.baidu.com/s/xxxxxxxxx",
        "code": "abcd",
    },
    "P08": {
        "link": "https://pan.baidu.com/s/xxxxxxxxx",
        "code": "abcd",
    },
    "P09": {
        "link": "https://pan.baidu.com/s/xxxxxxxxx",
        "code": "abcd",
    },
    "P10": {
        "link": "https://pan.baidu.com/s/xxxxxxxxx",
        "code": "abcd",
    },
}

# 发货记录文件路径
SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "delivery_log.json"
TEMPLATE_FILE = SCRIPT_DIR / "templates.json"


# ============================================================
# 数据管理
# ============================================================

def load_templates():
    """加载回复话术模板"""
    if not TEMPLATE_FILE.exists():
        print(f"[错误] 模板文件不存在: {TEMPLATE_FILE}")
        sys.exit(1)
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_log():
    """加载发货记录"""
    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"records": []}


def save_log(log_data):
    """保存发货记录"""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)


def add_record(product_id, product_name, price):
    """添加一条发货记录"""
    log = load_log()
    log["records"].append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "product_id": product_id,
        "product_name": product_name,
        "price": price,
    })
    save_log(log)


# ============================================================
# 回复生成
# ============================================================

def show_product_list(templates):
    """显示商品列表供选择"""
    print("\n" + "=" * 60)
    print("📦 商品列表")
    print("=" * 60)
    products = templates.get("products", {})
    for pid, info in products.items():
        print(f"  [{pid}] {info['name']}  |  {info['price']}")
    print("  [C]  通用回复（议价/咨询/售后）")
    print("  [Q]  退出")
    print("-" * 60)


def show_common_replies(templates):
    """显示通用回复模板"""
    common = templates.get("common_replies", {})
    print("\n" + "=" * 60)
    print("💬 通用回复模板")
    print("=" * 60)
    keys = list(common.keys())
    for i, key in enumerate(keys, 1):
        label_map = {
            "ask_price": "被问价格",
            "ask_content": "被问内容",
            "ask_discount": "被要求打折",
            "ask_custom": "被要求定制",
            "link_expired": "链接失效",
            "thank_you": "感谢支持",
            "ask_refund": "被要求退款",
        }
        label = label_map.get(key, key)
        print(f"  [{i}] {label}")
    print(f"  [Q]  返回")
    print("-" * 60)
    return keys


def generate_reply(product_id, templates):
    """为指定商品生成回复文案"""
    products = templates.get("products", {})
    product = products.get(product_id)

    if not product:
        print(f"[错误] 找不到商品: {product_id}")
        return None

    config = PRODUCT_CONFIG.get(product_id, {})
    reply = product["auto_reply"].format(
        link=config.get("link", "链接未配置"),
        code=config.get("code", "提取码未配置"),
    )

    return {
        "product_id": product_id,
        "name": product["name"],
        "price": product["price"],
        "reply": reply,
    }


# ============================================================
# 链接检查
# ============================================================

def check_links():
    """批量检查网盘链接有效性"""
    print("\n" + "=" * 60)
    print("🔗 链接有效性检查")
    print("=" * 60)
    print("（注意：百度网盘需要 Cookie 才能验证有效性）")
    print("（以下为链接配置状态检查）\n")

    all_ok = True
    for pid, config in PRODUCT_CONFIG.items():
        link = config.get("link", "")
        code = config.get("code", "")

        is_configured = "x" not in link.lower() and link != "你的网盘链接"

        if not is_configured:
            print(f"  [{pid}] ⚠️  链接未配置，请编辑 PRODUCT_CONFIG")
            all_ok = False
        elif not code or code == "提取码":
            print(f"  [{pid}] ⚠️  提取码未配置")
            all_ok = False
        else:
            print(f"  [{pid}] ✅ 已配置 | {link[:40]}... | 提取码: {code}")

    print("-" * 60)
    if all_ok:
        print("✅ 所有商品链接已配置")
    else:
        print("⚠️  部分链接未配置，请先编辑 auto_reply.py 中的 PRODUCT_CONFIG")

    print("\n💡 建议：每周运行一次此检查，确保链接没有失效。")


# ============================================================
# 统计功能
# ============================================================

def show_stats():
    """显示发货统计"""
    log = load_log()
    records = log.get("records", [])

    print("\n" + "=" * 60)
    print("📊 发货统计")
    print("=" * 60)

    if not records:
        print("  暂无发货记录")
        return

    # 按商品统计
    product_stats = {}
    for r in records:
        pid = r["product_id"]
        if pid not in product_stats:
            product_stats[pid] = {"count": 0, "name": r["product_name"], "total": 0}
        product_stats[pid]["count"] += 1
        # 解析价格（取中间值估算）
        price_str = r.get("price", "0")
        try:
            if "-" in price_str:
                low, high = price_str.replace("元", "").split("-")
                price = (float(low) + float(high)) / 2
            else:
                price = float(price_str.replace("元", ""))
        except ValueError:
            price = 0
        product_stats[pid]["total"] += price

    # 计算总体统计
    total_orders = len(records)
    total_revenue = sum(s["total"] for s in product_stats.values())

    # 按时间范围
    if records:
        first_date = records[0]["time"][:10]
        last_date = records[-1]["time"][:10]

    print(f"\n📅 时间范围: {first_date} ~ {last_date}")
    print(f"📦 总发货: {total_orders} 单")
    print(f"💰 预估收入: {total_revenue:.0f} 元")
    print(f"\n{'商品':<30} {'单量':>6} {'预估收入':>10}")
    print("-" * 50)
    for pid, stats in sorted(product_stats.items()):
        print(f"{stats['name']:<30} {stats['count']:>5}单  {stats['total']:>8.0f}元")
    print("=" * 60)

    # 日收入预估
    unique_days = len(set(r["time"][:10] for r in records)) or 1
    daily_avg = total_revenue / unique_days
    print(f"\n📈 日均预估收入: {daily_avg:.1f} 元")
    print(f"🎯 目标达成率: {total_revenue/1000*100:.0f}% （目标1000元/月）")

    # 最近10条记录
    print(f"\n📋 最近10条发货记录:")
    print("-" * 60)
    for r in records[-10:]:
        print(f"  {r['time']} | {r['product_name']} | {r['price']}")


# ============================================================
# 交互模式（主入口）
# ============================================================

def interactive_mode():
    """交互模式：选择商品 → 生成回复 → 记录发货"""
    templates = load_templates()

    while True:
        show_product_list(templates)
        choice = input("请选择商品编号 [P01-P10 / C / Q]: ").strip().upper()

        if choice == "Q":
            print("👋 再见！")
            break

        if choice == "C":
            # 通用回复子菜单
            common_mode(templates)
            continue

        if choice.startswith("P"):
            info = generate_reply(choice, templates)
            if info:
                print("\n" + "=" * 60)
                print(f"📋 {info['name']}  |  {info['price']}")
                print("=" * 60)
                print("\n📝 复制以下内容到闲鱼聊天窗口：\n")
                print("-" * 40)
                print(info["reply"])
                print("-" * 40)

                # 记录发货
                confirm = input("\n✅ 已发送？按回车确认并记录 (n=跳过): ").strip().lower()
                if confirm != "n":
                    add_record(info["product_id"], info["name"], info["price"])
                    print(f"✅ 已记录: {info['name']} - {datetime.now().strftime('%H:%M:%S')}")
                else:
                    print("⏭️  跳过记录")
        else:
            print("⚠️  请输入有效的商品编号（如 P01）")


def common_mode(templates):
    """通用回复子菜单"""
    keys = show_common_replies(templates)
    common = templates.get("common_replies", {})

    while True:
        choice = input("请选择回复类型 [1-7 / Q]: ").strip().upper()

        if choice == "Q":
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                key = keys[idx]
                reply = common[key]
                print("\n" + "-" * 40)
                print("📝 复制以下内容：\n")
                print(reply)
                print("-" * 40)
                input("\n按回车继续...")
                break
            else:
                print("⚠️  编号超出范围")
        except ValueError:
            print("⚠️  请输入数字")


# ============================================================
# 主入口
# ============================================================

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║         闲鱼自动发货辅助系统 v1.0                        ║
║         Xianyu Auto-Delivery Assistant                   ║
╚══════════════════════════════════════════════════════════╝
    """)

    if "--check" in sys.argv:
        check_links()
    elif "--stats" in sys.argv:
        show_stats()
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
