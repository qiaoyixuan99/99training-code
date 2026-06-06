import base64, requests, json, os

path = "D:/【99】training code/picture/14e126c6-9641-4d62-9a54-d2508600d98d.png"
with open(path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

body = {
    "model": "qwen-vl-max",
    "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        {"type": "text", "text": "请详细描述这张图片的内容。"},
    ]}]
}

r = requests.post(
    "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    headers={"Authorization": f"Bearer {os.environ["DASHSCOPE_API_KEY"]}", "Content-Type": "application/json"},
    json=body, timeout=120
)
print(json.dumps(r.json(), ensure_ascii=False, indent=2))
