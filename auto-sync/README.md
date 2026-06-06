# Git 自动同步系统

> **本地文件有变更 → 自动 git commit → 自动 git push → GitHub 实时同步**

不用再手动 `git add . && git commit && git push`，不用提醒我提交。文件保存后，自动推送到 GitHub。

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│  auto_commit_watcher.py  (每 120 秒检查一次)         │
│  ↓ 检测文件变更                                       │
│  ↓ git add -A                                        │
│  ↓ git commit -m "auto: add: xxx; update: x files"   │
│  ↓                                                   │
│  .git/hooks/post-commit  (每次 commit 后自动触发)     │
│  ↓ git push origin master                            │
│  ↓                                                   │
│  GitHub  ← 代码已同步 ✅                              │
└─────────────────────────────────────────────────────┘
```

两层自动化：
- **post-commit hook**：每次 `git commit` 后自动 `git push`
- **文件监视器**：定时检测文件变更，自动 `git commit`

两者组合 = 全自动同步。

---

## 📂 文件说明

| 文件 | 作用 |
|------|------|
| `auto_commit_watcher.py` | 核心监视器，定时检测变更 → 自动提交 |
| `start_watcher.bat` | Windows 启动脚本，双击即可后台运行 |
| `.git/hooks/post-commit` | Git 钩子，提交后自动推送 |

---

## 🚀 使用方法

### 方式一：开机自启（推荐，一劳永逸）

```
1. Win + R → 输入 shell:startup → 回车
2. 把 start_watcher.bat 快捷方式粘贴进去
3. 搞定。每次开机自动在后台运行。
```

### 方式二：手动启动

```bash
# 双击 start_watcher.bat
# 或者命令行启动
python auto-sync/auto_commit_watcher.py --interval 120
```

### 方式三：手动触发一次

```bash
# 只检查一次，有变更就提交+推送
python auto-sync/auto_commit_watcher.py --once
```

---

## 📊 常用命令

```bash
# 查看监视器运行状态 + 仓库状态
python auto-sync/auto_commit_watcher.py --status

# 前台运行（每60秒检查一次）
python auto-sync/auto_commit_watcher.py --interval 60

# 查看操作日志
cat auto-sync/watcher.log
```

---

## ⚙️ 配置说明

在 `auto_commit_watcher.py` 顶部可以修改：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DEFAULT_INTERVAL` | 120 秒 | 检测间隔，最小 10 秒 |
| `IGNORE_PATTERNS` | PID文件/日志/缓存 | 额外忽略的文件 |
| `LOG_FILE` | `auto-sync/watcher.log` | 日志路径 |

---

## 🔄 工作流程示例

```
14:00  你编辑了 商品文案.md
14:02  监视器检测到变更
14:02  自动 git add -A
14:02  自动 git commit -m "auto: update: 1 files"
14:02  post-commit hook 触发
14:02  git push origin master ✅
14:02  GitHub 已更新！
```

全程你只需要 **Ctrl+S 保存文件**。

---

## ⚠️ 注意事项

- 自动提交的 commit message 格式为 `auto: <摘要>`，和手动提交区分开来
- 如果 GitHub SSH 密钥未配置，push 会失败 → 先配好 `git@github.com` 密钥
- 停止监视器：任务管理器 → 结束 `python.exe` / `pythonw.exe` 进程
- 不要同时运行两个监视器（系统会检测并阻止）

---

## 🧪 验证是否生效

```bash
# 1. 启动监视器
python auto-sync/auto_commit_watcher.py --interval 60

# 2. 修改任意文件并保存

# 3. 60秒后检查
python auto-sync/auto_commit_watcher.py --status

# 4. 如果显示 "✅ 工作区干净" 说明已自动提交
#    如果显示 "✅ 所有提交已推送" 说明已自动推送到 GitHub
```
