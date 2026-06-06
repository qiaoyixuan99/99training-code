"""
闲鱼每日运营检查清单
====================
功能：引导完成每日运营任务，生成打卡记录

使用方法：
  python daily_tracker.py           # 当日第一次运行
  python daily_tracker.py --review  # 查看历史打卡记录

输出：daily_log.txt（每日打卡记录）

作者：闲鱼二号店项目
日期：2026-06-06
"""

import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置
# ============================================================

SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "daily_log.txt"

# 上架时间窗口
BEST_POST_TIME = "18:00 - 23:00"

# 每日任务清单
DAILY_TASKS = [
    {
        "id": 1,
        "name": "擦亮所有商品",
        "how": "打开闲鱼App → 我发布的 → 一键擦亮",
        "why": "擦亮 = 免费刷新曝光，每天一次别浪费",
        "time": "1分钟",
    },
    {
        "id": 2,
        "name": "回复未读消息",
        "how": "检查所有未读消息，优先回复咨询和下单的",
        "why": "回复速度直接影响流量分配，2小时内回复最佳",
        "time": "2-5分钟",
    },
    {
        "id": 3,
        "name": "上架 2-3 个新品",
        "how": "从商品文案库选 2-3 个还没上架的 → 复制文案 → 发布",
        "why": "日更是闲鱼权重最重要的指标之一，断更会降权",
        "time": "5-10分钟",
        "tip": "新商品建议在 18:00-23:00 发布，此时流量最高",
    },
    {
        "id": 4,
        "name": "检查昨日数据",
        "how": "打开闲鱼App → 我发布的 → 看每个商品的曝光量和想要的数",
        "why": "数据不会骗人，曝光<50的商品需要考虑优化或下架",
        "time": "3-5分钟",
    },
    {
        "id": 5,
        "name": "下架零曝光商品",
        "how": "找出上架超过7天但曝光<50的商品 → 下架",
        "why": "死链接会拉低整个账号的权重",
        "time": "1分钟",
    },
    {
        "id": 6,
        "name": "检查网盘链接",
        "how": "抽检1-2个出单最多的商品，确认网盘链接没失效",
        "why": "链接失效 = 差评 = 账号权重下降",
        "time": "1分钟",
    },
]

# 运营小贴士
TIPS = [
    "💡 回复率越高，系统给的流量越多。尽量做到有问必回。",
    "💡 好评率维持在 98% 以上，低于这个数要主动联系买家解决问题。",
    "💡 首图用文字+对比图的效果最好，纯产品图点击率低。",
    "💡 标题前 15 个字最重要——用户搜索只看到前 15 个字。",
    "💡 爆款链接不要改——一旦改了标题或首图，流量可能归零。",
]


# ============================================================
# 交互式清单
# ============================================================

def print_header():
    """打印标题"""
    now = datetime.now()
    print("""
╔══════════════════════════════════════════════════════════╗
║         闲鱼每日运营检查清单                             ║
║         Xianyu Daily Operations Checklist                ║
╚══════════════════════════════════════════════════════════╝
    """)
    print(f"📅 日期: {now.strftime('%Y-%m-%d %A')}")
    print(f"⏰ 时间: {now.strftime('%H:%M')}")
    print(f"🎯 目标: 日均收入 33 元（月入 1000 元）")
    print(f"📌 最佳上架时间: {BEST_POST_TIME}")
    print()


def run_checklist():
    """运行每日清单"""
    completed = []
    skipped = []

    for task in DAILY_TASKS:
        print("=" * 60)
        print(f"📋 任务 {task['id']}/6: {task['name']}")
        print(f"   预计用时: {task['time']}")
        print(f"   操作: {task['how']}")
        print(f"   原因: {task['why']}")
        if "tip" in task:
            print(f"   💡 {task['tip']}")
        print()

        while True:
            choice = input("   完成了吗？ [y=已完成 / n=跳过 / s=查看详情]: ").strip().lower()

            if choice == "y":
                completed.append(task)
                print("   ✅ 已标记完成\n")
                break
            elif choice == "n":
                skipped.append(task)
                print("   ⏭️  已跳过\n")
                break
            elif choice == "s":
                # 重新显示详情（已在上方，不再重复）
                print()
            else:
                print("   ⚠️  请输入 y / n / s")

    return completed, skipped


def print_summary(completed, skipped):
    """打印完成总结"""
    print("\n" + "=" * 60)
    print("📊 今日打卡总结")
    print("=" * 60)

    print(f"\n✅ 已完成: {len(completed)}/6")
    for task in completed:
        print(f"   ✅ {task['name']}")

    if skipped:
        print(f"\n⏭️  已跳过: {len(skipped)}/6")
        for task in skipped:
            print(f"   ⏭️  {task['name']}")

    # 完成率评价
    rate = len(completed) / 6
    if rate == 1.0:
        print("\n🏆 完美！全部完成，今日运营满分！")
    elif rate >= 0.8:
        print(f"\n👍 不错！完成了 {rate*100:.0f}%，保持节奏。")
    elif rate >= 0.5:
        print(f"\n⚠️  完成率 {rate*100:.0f}%，明天加油补上。")
    else:
        print(f"\n🔴 完成率偏低 {rate*100:.0f}%，断更对权重影响很大，明天务必补上。")

    # 随机小贴士
    import random
    print(f"\n{random.choice(TIPS)}")
    print()


def save_log(completed, skipped):
    """保存打卡记录"""
    now = datetime.now()
    log_entry = f"""
{'='*60}
打卡时间: {now.strftime('%Y-%m-%d %H:%M:%S')}
完成: {len(completed)}/6 项
{'-'*40}
完成项:
{chr(10).join(f'  ✅ {t["name"]}' for t in completed) if completed else '  （无）'}
跳过项:
{chr(10).join(f'  ⏭️  {t["name"]}' for t in skipped) if skipped else '  （无）'}
{'='*60}
"""

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"📝 打卡记录已保存到: {LOG_FILE}")


def show_review():
    """显示历史打卡记录"""
    if not LOG_FILE.exists():
        print("📝 暂无打卡记录，先运行 python daily_tracker.py 吧")
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # 统计
    entries = content.split("=" * 60)
    count = sum(1 for e in e if "打卡时间" in e)

    print("\n📊 历史打卡统计")
    print(f"   总打卡次数: {count}")
    print(f"\n最近记录:\n")
    print(content[-3000:])  # 最近几条


# ============================================================
# 主入口
# ============================================================

def main():
    if "--review" in sys.argv or "-r" in sys.argv:
        show_review()
        return

    print_header()
    completed, skipped = run_checklist()
    print_summary(completed, skipped)
    save_log(completed, skipped)

    print("👋 今日运营完成，明天见！")


if __name__ == "__main__":
    main()
