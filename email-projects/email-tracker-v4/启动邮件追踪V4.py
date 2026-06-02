"""邮件追踪 V4 启动器 — 双击此文件启动服务器并自动打开浏览器。"""

import sys
import threading
import webbrowser
import socket
import time
from pathlib import Path

# Ensure the app directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app import app

PORT = 5004
URL = f"http://127.0.0.1:{PORT}"


def server_already_running():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try:
        s.connect(("127.0.0.1", PORT))
        return True
    except (socket.error, ConnectionRefusedError):
        return False
    finally:
        s.close()


if __name__ == "__main__":
    if server_already_running():
        print("服务器已在运行，直接打开浏览器...")
        webbrowser.open(URL)
    else:
        print("正在启动邮件追踪 V4 服务器...")
        t = threading.Thread(
            target=app.run,
            kwargs={"host": "0.0.0.0", "port": PORT, "debug": False},
            daemon=True,
        )
        t.start()

        for _ in range(20):
            time.sleep(0.5)
            if server_already_running():
                break

        print(f"服务器已就绪：{URL}")
        webbrowser.open(URL)
        print("关闭此窗口将停止服务器。")

        try:
            t.join()
        except KeyboardInterrupt:
            print("\n服务器已停止。")
