"""
PyInstaller 打包脚本 — 生成独立 .exe

用法:
    python build_exe.py          # 打包为单文件 .exe
    python build_exe.py --onedir # 打包为文件夹 (启动更快)

输出: dist/QuantTrading工作站.exe
"""
import os
import sys
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(ROOT, "server")
DESKTOP_DIR = os.path.join(ROOT, "desktop")
DIST_DIR = os.path.join(ROOT, "dist")

def clean():
    """清理旧构建产物"""
    for d in ["dist", "build", "__pycache__"]:
        path = os.path.join(ROOT, d)
        if os.path.exists(path):
            shutil.rmtree(path)
    for d in ["dist", "build", "__pycache__"]:
        path = os.path.join(SERVER_DIR, d)
        if os.path.exists(path):
            shutil.rmtree(path)
    for f in os.listdir(ROOT):
        if f.endswith(".spec"):
            os.remove(os.path.join(ROOT, f))

def build(mode="onedir"):
    """运行 PyInstaller 打包"""
    clean()

    # PyInstaller 参数
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=QuantTrading工作站",
        f"--{mode}",
        "--console",  # 保留控制台窗口 (显示日志)
        "--clean",
        "--noconfirm",
    ]

    # 数据文件: 将 desktop/ 打包进去
    sep = ";" if sys.platform == "win32" else ":"
    cmd += [
        f"--add-data={DESKTOP_DIR}{sep}desktop",
    ]

    # 隐藏导入 (有些库 PyInstaller 检测不到)
    cmd += [
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=loguru",
        "--hidden-import=pandas",
        "--hidden-import=numpy",
        "--hidden-import=baostock",
    ]

    # 排除不需要的大型库
    cmd += [
        "--exclude-module=matplotlib",
        "--exclude-module=scipy",
        "--exclude-module=sklearn",
        "--exclude-module=xgboost",
        "--exclude-module=torch",
        "--exclude-module=redis",
        "--exclude-module=pyarrow",
    ]

    # 入口
    entry = os.path.join(SERVER_DIR, "main.py")
    cmd.append(entry)

    print(f"[BUILD] 模式: {mode}")
    print(f"[BUILD] 命令: {' '.join(cmd)}")

    os.chdir(ROOT)
    ret = os.system(" ".join(cmd))

    if ret == 0:
        dist_path = os.path.join(DIST_DIR, "QuantTrading工作站")
        if mode == "onefile":
            dist_path += ".exe"
        print(f"\n[OK] 打包完成: {dist_path}")
        print(f"[INFO] 将整个 dist/ 文件夹发给他人即可运行")
    else:
        print(f"\n[ERROR] 打包失败, 退出码: {ret}")
        sys.exit(1)

if __name__ == "__main__":
    mode = "onedir"
    if "--onefile" in sys.argv:
        mode = "onefile"
    elif "--onedir" in sys.argv:
        mode = "onedir"

    print("=" * 50)
    print("  QuantTrading Workstation — PyInstaller 打包")
    print("=" * 50)
    build(mode)
