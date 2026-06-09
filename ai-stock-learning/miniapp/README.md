# 微信小程序 — K线量化分析前端

## 技术栈

- 框架：微信原生框架（WXML / WXSS / JS）
- 图表：Canvas 2D API（自定义 K 线图）
- 数据源：东方财富公开 API
- 后端对接：Python Flask AI 引擎

## 页面结构

```
pages/
├── chart/          # 📈 行情页（默认首页）
│   ├── Canvas 2D K线图 + 多周期切换
│   ├── 拐点自动标注（峰/谷/趋势反转）
│   ├── MA 均线叠加（5/10/20/60）
│   ├── 支撑/压力线
│   ├── 搜索弹层（股票代码/名称搜索）
│   └── 实时行情展示
│
├── analysis/       # 🔍 AI 分析页
│   ├── 对接 Python 引擎（优先）
│   ├── 本地分析（降级方案）
│   ├── 技术指标状态（MA/MACD/RSI/趋势）
│   ├── 风险评估 + 信号汇总
│   └── 策略/预测结果展示
│
├── watchlist/      # ⭐ 自选股
│   ├── 自选列表（添加/删除）
│   ├── 实时行情刷新
│   └── 点击跳转行情页
│
└── profile/        # 👤 个人中心
    ├── 学习/分析统计
    ├── 分析历史记录
    └── 引擎状态检查
```

## 数据流

```
chart 页面 → market-data.js → 东方财富 API（wx.request）
    ↓ 用户点击拐点标签
analysis 页面
    ├── ai-engine.js → Python Flask (优先)
    │       └── /api/analyze_data  (K线数据直传)
    └── turning-points.js (降级)
```

## 开发

### 环境要求

- 微信开发者工具（最新版）
- 基础库版本 >= 2.9.0（支持 Canvas 2D）

### 本地调试

1. 打开微信开发者工具
2. 导入项目 → 选择 `ai-stock-learning/miniapp/`
3. 开发者工具右上角 → 详情 → 本地设置
   - ☑ 不校验合法域名、web-view、TLS 版本
4. 确保 Python Flask 引擎已启动（`cd ai-engine && python server.py`）

### AppID

- 正式：`wx9f087668ad188582`
- 测试：使用微信开发者工具提供的测试号

## 配置说明

| 文件 | 说明 |
|------|------|
| `app.json` | 页面路由 + TabBar 配置 + 权限声明 |
| `app.js` | 全局状态（currentStock、analysisHistory） |
| `app.wxss` | 全局样式（暗色主题） |
| `project.config.json` | 项目编译配置 |
| `project.private.config.json` | 个人私有配置（已在 .gitignore） |

## 服务层

| 模块 | 说明 |
|------|------|
| `services/market-data.js` | 东方财富 API 封装（K线 + 行情 + 搜索） |
| `services/ai-engine.js` | Python Flask API 对接（健康检查 + 分析请求） |
| `utils/turning-points.js` | 拐点检测算法（局部极值 + 强度评分） |
