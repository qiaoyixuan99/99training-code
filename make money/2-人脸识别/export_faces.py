"""
人脸照片自动识别导出工具
=======================
用法: 把个人信息文件夹丢进 inventory/，运行本脚本即可。
人脸照片会自动导出到 face_export/，以文件夹名命名。

纯离线运行，首次自动安装 opencv-python + numpy。
"""
import sys
import subprocess
from pathlib import Path


# ── 自动环境检测 & 安装 ──────────────────────────────────────────
def ensure_deps():
    missing = []
    for mod, pkg in [("cv2", "opencv-python"), ("numpy", "numpy")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"[环境] 缺少依赖: {', '.join(missing)}，正在自动安装...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q"] + missing,
            stdout=sys.stdout, stderr=sys.stderr,
        )
        print("[环境] 安装完成，请重新运行脚本")
        sys.exit(0)


ensure_deps()

# ── 依赖就绪后才 import ──────────────────────────────────────────
import cv2
import numpy as np
import shutil

# ── 配置 ──────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
SOURCE_DIR = SCRIPT_DIR / "inventory"
OUTPUT_DIR = SCRIPT_DIR / "face_export"

# ── 人脸检测器（全局初始化一次）───────────────────────────────────
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def get_max_face_area(image_path: Path) -> int:
    """返回图片中最大人脸面积（像素），没有人脸返回 0。"""
    with open(str(image_path), "rb") as f:
        img_bytes = np.frombuffer(f.read(), np.uint8)
    img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return 0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    if len(faces) == 0:
        return 0

    return max(fw * fh for (_, _, fw, fh) in faces)


def main():
    if not SOURCE_DIR.exists():
        print(f"❌ 请创建 inventory 文件夹并放入人员子文件夹: {SOURCE_DIR}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    success_count = 0

    for person_dir in sorted(SOURCE_DIR.iterdir()):
        if not person_dir.is_dir():
            continue

        folder_name = person_dir.name
        jpg_files = list(person_dir.glob("*.jpg")) + list(person_dir.glob("*.JPG"))

        if not jpg_files:
            print(f"[跳过] {folder_name} — 无图片")
            continue

        # 优先：文件名匹配 face_img
        face_img_files = [f for f in jpg_files if "face_img" in f.stem.lower()]
        if face_img_files:
            best_file = face_img_files[0]
            print(f"[文件名] {folder_name}/{best_file.name}")
        else:
            # 兜底：人脸检测
            best_file = None
            best_area = 0
            for img_file in jpg_files:
                area = get_max_face_area(img_file)
                print(f"  {folder_name}/{img_file.name} — 人脸面积: {area} px")
                if area > best_area:
                    best_area = area
                    best_file = img_file

            if best_file is None or best_area == 0:
                print(f"[警告] {folder_name} — 未检测到人脸，跳过")
                continue
            print(f"[人脸检测] {folder_name}/{best_file.name} (面积: {best_area} px)")

        ext = best_file.suffix
        dst = OUTPUT_DIR / f"{folder_name}{ext}"
        shutil.copy2(str(best_file), str(dst))
        print(f"  → {dst.name}")
        success_count += 1

    print(f"\n完成: {success_count} 张人脸照片 → {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
