"""
Git 自动提交 + 推送监视器
==========================
监控仓库文件变更 → 自动 git add + commit → 触发 post-commit hook → 自动 push

原理：
  1. 每隔 N 秒检查 git status
  2. 发现有变更 → 自动 git add -A
  3. 生成有意义的 commit message → git commit
  4. post-commit hook 自动执行 git push

使用方法：
  python auto_commit_watcher.py                 # 前台运行，默认120秒检查一次
  python auto_commit_watcher.py --interval 60   # 每60秒检查一次
  python auto_commit_watcher.py --once          # 只检查一次（适合手动触发）
  python auto_commit_watcher.py --status        # 查看监视器运行状态

开机自启：
  将 start_watcher.bat 放到 Windows 启动文件夹：
  Win+R → shell:startup → 粘贴 start_watcher.bat 快捷方式

作者：全仓库自动同步系统
日期：2026-06-06
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

# Windows GBK 编码兼容：强制 stdout 使用 UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# 配置
# ============================================================

# 仓库根目录（脚本所在目录的上级）
REPO_ROOT = Path(__file__).resolve().parent.parent

# 数据文件存放位置
SCRIPT_DIR = Path(__file__).resolve().parent
PID_FILE = SCRIPT_DIR / ".watcher_pid.json"
LOG_FILE = SCRIPT_DIR / "watcher.log"

# 默认检查间隔（秒）
DEFAULT_INTERVAL = 120

# 要忽略的文件模式（不会被自动提交）
# 注意：这里补充 .gitignore 之外的额外忽略规则
IGNORE_PATTERNS = [
    ".watcher_pid.json",
    "watcher.log",
    "__pycache__",
    ".pyc",
    ".DS_Store",
]


# ============================================================
# 日志
# ============================================================

def log(msg: str):
    """写日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ============================================================
# PID 管理（防止重复启动）
# ============================================================

def write_pid(interval: int):
    """写入PID文件"""
    PID_FILE.write_text(json.dumps({
        "pid": os.getpid(),
        "started_at": datetime.now().isoformat(),
        "interval": interval,
        "repo": str(REPO_ROOT),
    }), encoding="utf-8")


def remove_pid():
    """删除PID文件"""
    if PID_FILE.exists():
        PID_FILE.unlink()


def check_running() -> dict | None:
    """检查是否有另一个监视器在运行"""
    if not PID_FILE.exists():
        return None
    try:
        data = json.loads(PID_FILE.read_text(encoding="utf-8"))
        pid = data.get("pid", 0)
        # 检查进程是否还在运行
        if pid:
            try:
                os.kill(pid, 0)  # 信号0不杀进程，只检查是否存在
                return data
            except OSError:
                # 进程不存在，清理残留PID文件
                remove_pid()
                return None
    except (json.JSONDecodeError, FileNotFoundError):
        remove_pid()
    return None


# ============================================================
# Git 操作
# ============================================================

def run_git(args: list[str], capture: bool = True) -> tuple[int, str, str]:
    """运行 git 命令"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(REPO_ROOT),
            capture_output=capture,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        return result.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Git command timed out"
    except FileNotFoundError:
        return -1, "", "Git not found in PATH"


def get_status() -> list[dict]:
    """获取工作区状态（解析 git status --porcelain）"""
    code, stdout, stderr = run_git(["status", "--porcelain"])
    if code != 0:
        log(f"⚠️  git status 失败: {stderr}")
        return []

    changes = []
    for line in stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 格式: XY filename (X=暂存区状态, Y=工作区状态)
        status_code = line[:2]
        file_path = line[3:].strip()

        # 跳过忽略的文件
        if any(pattern in file_path for pattern in IGNORE_PATTERNS):
            continue

        changes.append({
            "status": status_code,
            "file": file_path,
        })

    return changes


def generate_commit_message(changes: list[dict]) -> str:
    """根据变更内容生成有意义的 commit message"""
    if not changes:
        return "auto: no changes"

    # 按状态分类
    new_files = [c for c in changes if c["status"].strip() == "??"]  # 未跟踪
    modified = [c for c in changes if "M" in c["status"]]
    deleted = [c for c in changes if "D" in c["status"]]
    added = [c for c in changes if "A" in c["status"]]

    parts = []
    if new_files:
        # 提取新增的目录/文件名作为摘要
        dirs = set()
        for f in new_files[:10]:  # 最多取10个文件
            parts_path = Path(f["file"]).parts
            if len(parts_path) > 1:
                dirs.add(str(Path(f["file"]).parent))
            else:
                dirs.add(f["file"])
        if len(new_files) > 10:
            dirs.add(f"等{len(new_files)}个文件")
        parts.append(f"add: {', '.join(sorted(dirs)[:5])}")

    if modified:
        parts.append(f"update: {len(modified)} files")

    if deleted:
        parts.append(f"delete: {len(deleted)} files")

    if not parts:
        parts.append("update files")

    return "auto: " + "; ".join(parts)


def auto_commit() -> bool:
    """
    检查变更 → 暂存 → 提交
    返回 True 表示有提交发生
    """
    changes = get_status()

    if not changes:
        return False

    log(f"检测到 {len(changes)} 个变更:")
    for c in changes[:15]:
        log(f"  {c['status']}  {c['file']}")
    if len(changes) > 15:
        log(f"  ... 还有 {len(changes) - 15} 个文件")

    # git add -A (暂存所有变更)
    code, stdout, stderr = run_git(["add", "-A"])
    if code != 0:
        log(f"❌ git add 失败: {stderr}")
        return False

    # 生成 commit message 并提交
    message = generate_commit_message(changes)
    code, stdout, stderr = run_git(["commit", "-m", message])
    if code != 0:
        if "nothing to commit" in stderr.lower():
            return False
        log(f"❌ git commit 失败: {stderr}")
        return False

    log(f"✅ 已提交: {message}")
    log(f"   post-commit hook 将自动推送...")
    return True


# ============================================================
# 监视器主循环
# ============================================================

def watch_loop(interval: int):
    """主监视循环"""
    log("=" * 50)
    log("🚀 Git 自动提交监视器已启动")
    log(f"   仓库: {REPO_ROOT}")
    log(f"   检查间隔: {interval} 秒")
    log(f"   分支: {get_current_branch()}")
    log(f"   PID: {os.getpid()}")
    log("   按 Ctrl+C 停止")
    log("=" * 50)

    write_pid(interval)

    try:
        while True:
            try:
                committed = auto_commit()
                if committed:
                    log(f"⏰ 下次检查: {interval} 秒后")
                # 即使没有变更也定期输出心跳，方便确认在运行
            except Exception as e:
                log(f"❌ 检查出错: {e}")

            time.sleep(interval)

    except KeyboardInterrupt:
        log("\n⏹️  收到停止信号，正在退出...")
    finally:
        remove_pid()
        log("👋 监视器已停止")


def get_current_branch() -> str:
    """获取当前分支名"""
    code, stdout, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    return stdout if code == 0 else "unknown"


def run_once():
    """手动触发一次检查+提交"""
    log("🔍 手动检查一次...")
    committed = auto_commit()
    if committed:
        log("✅ 提交完成，post-commit hook 将自动推送")
    else:
        log("✅ 无变更")


def show_status():
    """显示监视器和仓库状态"""
    print(f"\n{'='*50}")
    print("📊 自动同步系统状态")
    print(f"{'='*50}")

    # 仓库信息
    print(f"\n📂 仓库: {REPO_ROOT}")
    print(f"🌿 分支: {get_current_branch()}")

    # 监视器状态
    running = check_running()
    if running:
        started = running.get("started_at", "unknown")
        interval = running.get("interval", "unknown")
        print(f"🟢 监视器: 运行中")
        print(f"   启动时间: {started}")
        print(f"   检查间隔: {interval} 秒")
        print(f"   PID: {running.get('pid')}")
    else:
        print("🔴 监视器: 未运行")

    # 当前变更
    changes = get_status()
    if changes:
        print(f"\n📝 当前未提交的变更: {len(changes)} 个")
        for c in changes[:10]:
            print(f"   {c['status']}  {c['file']}")
        if len(changes) > 10:
            print(f"   ... 还有 {len(changes) - 10} 个")
    else:
        print(f"\n✅ 工作区干净，无未提交变更")

    # 未推送的提交
    code, stdout, _ = run_git(["log", f"origin/{get_current_branch()}..HEAD", "--oneline"])
    if code == 0 and stdout:
        unpushed = [l for l in stdout.split("\n") if l.strip()]
        print(f"\n📤 未推送的提交: {len(unpushed)} 个")
        for line in unpushed[:5]:
            print(f"   {line}")
    elif code == 0:
        print(f"\n✅ 所有提交已推送")

    # 最近日志
    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if lines:
            print(f"\n📋 最近日志 (最后5条):")
            for line in lines[-5:]:
                print(f"   {line.rstrip()}")

    print(f"\n{'='*50}\n")


# ============================================================
# 主入口
# ============================================================

def main():
    # 切换到仓库根目录
    os.chdir(str(REPO_ROOT))

    # 命令行参数处理
    if "--status" in sys.argv or "-s" in sys.argv:
        show_status()
        return

    if "--once" in sys.argv or "-1" in sys.argv:
        run_once()
        return

    # 检查重复启动
    running = check_running()
    if running:
        print(f"⚠️  监视器已在运行中 (PID: {running.get('pid')})")
        print(f"   启动时间: {running.get('started_at')}")
        print(f"   如需重启，先删除 {PID_FILE}")
        print(f"   或运行 python auto_commit_watcher.py --status 查看状态")
        return

    # 解析间隔参数
    interval = DEFAULT_INTERVAL
    for i, arg in enumerate(sys.argv):
        if arg == "--interval" and i + 1 < len(sys.argv):
            try:
                interval = max(10, int(sys.argv[i + 1]))  # 最小10秒
            except ValueError:
                pass

    # 启动监视循环
    watch_loop(interval)


if __name__ == "__main__":
    main()
