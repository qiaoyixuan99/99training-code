# 📡 数据源与数据库方案

---

## 1. 数据源选型

### 1.1 行情数据源对比

| 数据源 | 类型 | 费用 | 数据覆盖 | 更新频率 | 推荐用途 |
|--------|------|------|---------|---------|---------|
| **AKShare** | Python库 | 免费 | A股全量+指数+基金+期货 | 交易日实时 | ⭐ 首选主力 |
| **Baostock** | Python库 | 免费 | A股历史日线/分钟线+财务 | 交易日更新 | 历史数据补充 |
| **Tushare Pro** | API | 免费(限额)/付费 | A股全量+高频+财务+另类 | 实时+历史 | 高级功能备用 |
| **新浪财经** | HTTP | 免费 | 实时报价+分时 | 实时 | 实时行情补充 |
| **东方财富** | HTTP | 免费 | 实时行情+资金流向 | 实时 | 资金流向数据 |
| **聚宽/米筐** | 平台API | 部分免费 | 全量+因子库 | 日级 | 因子参考 |

### 1.2 推荐数据源组合

```
主力方案: AKShare (主) + Baostock (辅) + 东方财富 (实时)

AKShare  → 历史日线/周线/月线、指数、行业板块、龙虎榜
Baostock → 历史分钟线、财务三表 (利润表/资产负债表/现金流)
东方财富  → 实时报价、资金流向、盘口数据
```

### 1.3 数据获取策略

```python
# data_engine/fetcher.py 伪代码架构

class DataFetcher:
    """多数据源统一适配器"""

    adapters = {
        'akshare': AKShareAdapter(),      # 主力
        'baostock': BaostockAdapter(),    # 补充
        'eastmoney': EastMoneyAdapter(),  # 实时
    }

    def get_kline(self, symbol, period, start, end):
        """智能路由：优先缓存 → AKShare → Baostock"""
        if cached := self.cache.get(symbol, period, start, end):
            return cached
        try:
            data = self.adapters['akshare'].get_kline(...)
        except Exception:
            data = self.adapters['baostock'].get_kline(...)
        self.cache.set(symbol, period, data)
        return data

    def get_realtime_quote(self, symbols):
        """实时行情走东方财富"""
        return self.adapters['eastmoney'].get_realtime(symbols)

    def get_financials(self, symbol):
        """财务报表走 Baostock（数据更全）"""
        return self.adapters['baostock'].get_financials(symbol)
```

---

## 2. 数据库设计

### 2.1 存储架构总览

```
┌──────────────────────────────────────────────────┐
│                   Storage Layers                   │
├────────────┬─────────────────┬───────────────────┤
│  SQLite    │  Parquet Files   │  Redis (可选)     │
│  元数据     │  行情数据         │  实时缓存         │
├────────────┼─────────────────┼───────────────────┤
│ • 股票信息  │ • 日线行情       │ • 实时报价        │
│ • 自选股    │ • 分钟行情       │ • 最新K线         │
│ • 策略记录  │ • 财务数据       │ • 计算结果缓存    │
│ • 回测记录  │ • 指标缓存       │                   │
│ • 用户配置  │ • 选股结果缓存   │                   │
└────────────┴─────────────────┴───────────────────┘
```

### 2.2 SQLite 表设计 (元数据)

```sql
-- 股票基本信息表
CREATE TABLE stock_info (
    symbol      TEXT PRIMARY KEY,     -- 股票代码 (sh.600000)
    name        TEXT NOT NULL,        -- 股票名称
    industry    TEXT,                 -- 所属行业
    market      TEXT,                 -- 市场 (sh/sz/bj)
    list_date   DATE,                 -- 上市日期
    is_st       INTEGER DEFAULT 0,    -- 是否ST
    updated_at  TIMESTAMP
);

-- 自选股表
CREATE TABLE watchlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL,
    group_name  TEXT DEFAULT '默认',  -- 分组
    sort_order  INTEGER DEFAULT 0,   -- 排序
    added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (symbol) REFERENCES stock_info(symbol)
);

-- 策略表
CREATE TABLE strategy (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT,
    code        TEXT NOT NULL,        -- Python策略代码
    params      TEXT,                 -- JSON 参数字典
    created_at  TIMESTAMP,
    updated_at  TIMESTAMP
);

-- 回测记录表
CREATE TABLE backtest_record (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id     INTEGER,
    symbol          TEXT,              -- NULL = 批量回测
    params          TEXT,              -- JSON 回测参数
    start_date      DATE,
    end_date        DATE,
    sharpe_ratio    REAL,
    win_rate        REAL,
    max_drawdown    REAL,
    annual_return   REAL,
    total_return    REAL,
    profit_loss_ratio REAL,
    trade_count     INTEGER,
    result_path     TEXT,              -- 详细结果Parquet路径
    created_at      TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategy(id)
);

-- 用户配置表
CREATE TABLE user_config (
    key         TEXT PRIMARY KEY,
    value       TEXT,                  -- JSON
    updated_at  TIMESTAMP
);
```

### 2.3 Parquet 文件存储 (行情数据)

```
data/market/
├── day/                         # 日线行情
│   ├── sh.600000.parquet        # 单只股票一个文件
│   ├── sh.600519.parquet        # 列式存储：date/open/high/low/close/volume/amount
│   └── ...
├── min5/                        # 5分钟线
│   ├── sh.600000.parquet
│   └── ...
├── index/                       # 指数行情
│   ├── sh.000001.parquet        # 上证指数
│   └── ...
└── adjusted/                    # 复权因子
    └── adj_factor.parquet

# 每只股票一个 Parquet 文件的好处：
# 1. 回测时只读取需要的股票，IO最小
# 2. 列式存储，只读 OHLCV 列，跳过其他
# 3. 支持谓词下推过滤日期范围
# 4. Snappy/Zstd 压缩，存储省空间
```

### 2.4 Redis 缓存设计 (可选)

```
Key Pattern                          │ Type  │ TTL   │ 说明
─────────────────────────────────────┼───────┼───────┼──────────
quote:realtime:{symbol}              │ Hash  │ 60s   │ 实时报价快照
kline:latest:{symbol}:{period}       │ ZSet  │ 300s  │ 最近N根K线
screen:result:{task_id}              │ String│ 600s  │ 选股结果JSON
backtest:progress:{task_id}          │ String│ 600s  │ 回测进度
indicator:{symbol}:{name}:{params}   │ String│ 3600s │ 指标计算结果
```

---

## 3. 数据更新机制

### 3.1 历史数据初始化

```
首次使用流程:
1. 获取全量A股列表 (AKShare: stock_info_a_code_name)
2. 下载所有股票历史日线 (1990至今，约5000只)
3. 复权因子计算 (前复权/后复权)
4. 存储为 Parquet 格式
5. 建立 SQLite 元数据索引

预计: 全量日线数据约 2-5 GB (Parquet压缩后)
```

### 3.2 增量更新

```
每日更新 (收盘后自动触发):
1. 下载当日所有股票日线数据
2. 追加到对应 Parquet 文件
3. 更新 SQLite 元数据表

盘中更新 (实时):
1. 自选股实时行情 WebSocket 推送
2. Redis 缓存最新报价 (60s TTL)
3. 前端 WebSocket 订阅更新
```

---

## 4. 数据安全与隐私

```
✅ 所有数据本地存储，不上传任何服务器
✅ 策略代码本地保存，完全自主可控
✅ 回测记录仅存在于本地数据库
✅ 无任何遥测/数据收集
```
