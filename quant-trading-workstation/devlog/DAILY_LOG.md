# 📝 开发日志

> 按日期倒序记录每天做了什么、遇到什么问题、怎么解决的

---

## 模板（每次开发前复制）

```markdown
## 2026-06-XX

### 今日目标
- [ ] 任务1
- [ ] 任务2

### 实际完成
- [x] 完成的项

### 遇到的问题
1. **问题描述**
   - 原因: 
   - 解决: 

### 关键决策
- 决策内容 + 理由

### 明日计划
- 
```

---

## 2026-06-09

### 今日目标
- [x] 需求分析 → 架构设计
- [x] 项目文件夹结构搭建
- [x] 任务清单拆分 (9 Phase)
- [x] 文档体系建立 (架构/数据源/算法)
- [x] 后端框架代码 (FastAPI入口 + 8个API路由)
- [x] 前端框架代码 (Electron + React + Zustand + API层)
- [x] 核心引擎骨架 (数据引擎/缠论引擎/回测引擎/选股引擎)

### 实际完成
- 项目 `quant-trading-workstation/` 创建完成，31个文件
- 4份核心文档: TASK_LIST / ARCHITECTURE / DATA_SOURCES / ALGORITHMS
- devlog 进度追踪体系建立

### 关键决策
- **前端 Electron + React + TypeScript**: 跨平台桌面应用，Vite 构建
- **K线图 TradingView Lightweight Charts**: 专业级 Canvas 渲染
- **后端 Python FastAPI**: 原生支持 NumPy/Pandas，量化必备
- **存储 SQLite + Parquet + Redis**: 本地化方案，不上传数据
- **回测 NumPy 向量化 + Numba JIT**: 达到 300只/3分钟 目标
- **数据源 AKShare(主) + Baostock(辅)**: 免费 + 稳定

### 遇到的问题
1. **Python 3.14 + 依赖兼容性**: pydantic-settings 在新版 Python 中有兼容问题
   - 解决: 改用纯 Python 类替代 pydantic_settings，减少外部依赖
2. **npm 网络限制**: 无法访问 npm registry 和 npmmirror (ETIMEDOUT)
   - 解决: 放弃 Electron+React 方案，改用纯 HTML+CDN 单文件前端
3. **端口 8000 僵尸进程**: 多次重启后端口被多个僵尸进程占用
   - 解决: 切到端口 8001

### 关键决策
- **ADK-005: 前端从 Electron+React 降级为纯 HTML+Vanilla JS**
  理由: 网络限制无法 npm install；纯 HTML 方案零依赖、零构建，同样能展示 K 线图
  代价: 失去组件化能力，后续功能复杂后可能需要迁移回 React
- **端口变更**: 8000 → 8001（避开僵尸进程）

### 实际产出
- 后端: FastAPI + AKShare 真实数据拉取 ✅ → 可提供K线接口
- 前端: app.html 单文件应用 (Lightweight Charts CDN) ✅ → 可展示K线图
- 全栈打通 ✅ → `http://127.0.0.1:8001/` 可用


### 明日计划
- 用浏览器打开 `http://127.0.0.1:8001/` 验证完整功能
- 实现缠论引擎的包含处理 + 分型识别
- 实现缠论 API 路由

---

## 2026-06-09 (续) — Bug修复

### 问题
1. **前端报错**: "Cannot read properties of null (reading 'setData')"
2. **API 500错误**: AKShare 无法连接外部数据源

### 根本原因
- **unpkg.com CDN 被屏蔽** → Lightweight Charts 库加载失败 → `candleSeries` 为 null
- **East Money API 被屏蔽** → AKShare `stock_zh_a_hist()` 连接断开 (RemoteDisconnected)

### 修复
1. CDN 切换: `unpkg.com` → `cdn.jsdelivr.net`（中国大陆可访问）
2. 前端防御性编程:
   - `initChart()`: 检查 `createChart` 是否存在，失败时显示友好提示
   - `renderChart()`: 检查 `candleSeries`/`volumeSeries`/`chart` 非 null
3. 数据源切换: AKShare(主) → **Baostock(主) + AKShare(备)**
   - 新增 `_fetch_baostock_kline()` 方法
   - 自动登录 Baostock
   - 失败时自动回退 AKShare

### 验证
- ✅ `/api/v1/market/kline/000001?limit=2` → 平安银行数据
- ✅ `/api/v1/market/kline/600519?limit=2` → 贵州茅台数据
- ✅ `/api/v1/market/stock-list` → 5527只A股
- ✅ 前端HTML使用 jsdelivr CDN

---

## 2026-06-09 (续2) — CDN离线化 + 进程管理

### 问题
1. **jsdelivr CDN 在浏览器端仍被屏蔽** → 图表库加载失败
2. **浏览器首次访问时 `candleSeries` 为 null** → "Cannot read properties of null" 报错
3. **多个 Python 僵尸进程** → 端口被占、旧代码不更新 (reload 检测不到 main.py 变更)

### 修复
1. **CDN → 本地静态文件**: 
   - 下载 lightweight-charts.js (161KB) 到 `desktop/static/`
   - HTML 引用 `/static/lightweight-charts.js`
   - 后端显式路由 `@app.get("/static/lightweight-charts.js")` (避免 FastAPI StaticFiles mount 问题)
2. **initChart 防御性检查**: 检查 `createChart` 是否存在、容器是否存在、null guard
3. **renderChart null guard**: 检查 `candleSeries`/`volumeSeries`/`chart` 非 null
4. **启动脚本**: 先 `taskkill /F /IM python.exe` 清理僵尸进程，再用 `reload=False` 启动
5. **双启动方式**: `.bat` (cmd) + `.vbs` (Unicode-safe for 中文路径 `【99】`)

### 验证
- ✅ `/static/lightweight-charts.js` → 161KB JavaScript 正确返回
- ✅ `/` → HTML 使用本地静态文件引用
- ✅ `/api/v1/market/kline/000001` → Baostock 真实数据
- ✅ 启动脚本: .vbs 双击可启动（原生 Unicode 支持）

---

## 2026-06-09 (续3) — 实时行情 + 技术指标 + 打包方案

### 用户需求
1. 能否实现实时更新？
2. 能否打包给他人使用自动适配？
3. 只有蜡烛图，完善图表曲线，应用最准确的算法。

### 实现

#### 1. 实时行情更新
- **后端**: 新增新浪财经 API 适配层 `_parse_sina_realtime()`
  - 盘中取 `hq.sinajs.cn` 实时数据（无需认证）
  - 非盘中自动回退 Baostock 日线数据
  - 使用 `httpx` (已有依赖)
- **前端**: 5秒轮询 `pollRealtime()` + 交易时段检测 `isTradingHours()`
  - 周一至周五 9:30-15:05 自动轮询
  - 非交易时段显示"已收盘"状态
  - 实时更新行情面板 (价格/涨跌幅/成交量/数据源标识)
  - 工具栏显示实时状态指示灯 (绿=在线, 红=收盘, 灰=关闭)

#### 2. 图表曲线 — 业界标准算法
- **MA 均线系**: SMA(5)+SMA(10)+SMA(20)+SMA(60)
  - 滑动窗口增量计算 O(n)，非每次重算
- **Bollinger Bands (布林带)**: 中轨=MA(20), 上下=中轨±2σ
  - 总体标准差公式 σ = sqrt(Σ(x-μ)²/n)
- **MACD 指标**: DIF=EMA(12)-EMA(26), DEA=EMA(DIF,9), 柱=2*(DIF-DEA)
  - EMA 使用标准指数平滑 α=2/(n+1), 起始用SMA种子
- **双面板架构**: 主图(K线+MA+BB) + 副图(MACD柱+DIF/DEA线)
  - 时间轴同步 `subscribeVisibleTimeRangeChange`
  - 底部图例说明各线颜色

#### 3. 打包分发方案
- **`setup_portable.bat`**: 一键安装脚本
  - 自动检测 Python 版本
  - pip 安装依赖 (自动回退清华镜像)
  - 创建桌面快捷方式
  - 复制即用，无需手动配置
- **`build_exe.py`**: PyInstaller 打包脚本
  - 支持 `--onefile` 单文件 / `--onedir` 文件夹模式
  - 自动添加隐藏导入 (uvicorn/baostock/pandas)
  - 排除大型无用库 (torch/matplotlib/sklearn)
  - 输出可直接分发的独立 .exe

### 关键决策
- **图表计算放前端**: 纯 JS 数学运算，减少后端负载，指标即时切换
- **EMA 种子用 SMA 而非首值**: 与业界标准 (TradingView/同花顺) 一致
- **打包推荐 onedir 模式**: 启动快、更新方便、比 onefile 少解压开销

### 验证
- ✅ 前端技术指标: MA5/10/20/60 + BB上中下 + MACD(DIF/DEA/柱)
- ✅ 实时轮询: 5秒周期，交易时段检测
- ✅ 后端新浪接口: httpx 请求 + GBK 解码 + 字段解析
- ✅ 打包脚本: 自动依赖安装 + 桌面快捷方式

---

## 2026-06-09 (续4) — 缠论引擎完整实现 + K线分时显示

### 用户需求
将K线细分为分时显示，完善缠论分析，细化分析每一个拐点/异常点，基于全局和局部多维度分析。

### 实现

#### 1. K线分时显示
- **后端**: `fetcher.py` 新增 `_fetch_akshare_intraday()` 方法
  - 支持 5分钟/15分钟/30分钟/60分钟 K线周期
  - 分时周期走 AKShare `stock_zh_a_hist()` 接口
- **前端**: Dashboard 周期选择器新增分时选项，KLineChart 适配分时时间格式

#### 2. 缠论引擎完整实现 (5个新模块 + 1个改写)

| 模块 | 文件 | 核心功能 |
|------|------|----------|
| **分型识别** | fractal.py | K线包含处理 (上升/下降合并) + 顶底分型检测 + 交替验证 |
| **笔** 🆕 | stroke.py | 连接交替分型构建上升/下降笔，力度计算，最小5K线约束 |
| **线段** 🆕 | segment.py | ≥3笔+重叠区间构建线段，特征序列分析，线段背驰检测 |
| **中枢** 🆕 | center.py | ZG=min(高)/ZD=max(低)/ZZ=中轴，3段重叠构成，扩展合并，引力分析 |
| **买卖点** 🆕 | buy_sell_point.py | MACD背驰判定一二三类买卖点，3验证器+置信度评分 |
| **分析器** 🆕 | chan_analyzer.py | 11步全流程：全局趋势+市场阶段+结构健康+局部分析+拐点细化+5类异常检测+信号汇总 |

#### 3. 多维度分析体系

**全局维度**：
- MA均线排列趋势 (多头/空头/缠绕)
- 市场阶段 (吸筹/上涨/派发/下跌/震荡)
- 结构健康度评分 (0-100)
- 多周期共振判断

**局部维度**：
- 当前价格距支撑/阻力距离
- 风险等级 (高危/警告/正常/低风险)
- 最近分型/中枢位置

**拐点细化**：每个分型 → 局部振幅 + 量比 + 趋势位置(领先/反转) + 级别(major/medium/minor) + 端点状态

**异常点检测 (5类)**：
1. 量能异常 (放量>3x均量 / 缩量<0.3x)
2. 价格缺口 (跳空 + 回补判断)
3. 背驰 (顶背驰/底背驰)
4. 假突破 (突破中枢后收盘回落)
5. 异常振幅 (>8%)

#### 4. API 端点 (5个)
- `POST /api/v1/chan/analyze/{symbol}` — 完整多维度分析
- `GET /api/v1/chan/quick/{symbol}` — 快速摘要
- `GET /api/v1/chan/points/{symbol}` — 买卖点
- `GET /api/v1/chan/anomalies/{symbol}` — 异常点
- `GET /api/v1/chan/turning-points/{symbol}` — 拐点详情

#### 5. 前端页面
- **KLineChart 组件**: 图表叠加中枢矩形/笔连线/分型标记/买卖点信号 + 图例
- **chan-theory 页面**: K线图+全局分析面板+局部分析面板+拐点表+异常表+信号表+结构树

### 遇到的Bug及修复
1. **`AttributeError: 'dict' object has no attribute 'dtype'`** — Series和dict混用
   - 修复: `process_containment()` 统一转为 dict 格式
2. **`KeyError: 'inside_center'`** — 空中枢时返回字典缺少字段
   - 修复: `analyze_center_gravity()` 空列表路径添加 `inside_center: False`
3. **分型索引错位** — 包含处理后DataFrame行数减少导致索引不匹配
   - 修复: 直接用原始df检测分型，而非包含处理后的df

### 验证
- ✅ 合成数据 (200条): 分型→笔→线段→中枢 全链路通过
- ✅ 贵州茅台 600519: 36分型, 11笔, 3中枢, 2买点 (7-8月背驰), 健康度82
- ✅ 平安银行 000001: 强多头趋势正确识别
- ✅ 比亚迪 002594: 8分型, 2笔, 26异常点
- ✅ 5个API端点全部注册成功
