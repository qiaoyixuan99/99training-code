// 示例K线数据 — 用于演示拐点分析（无需网络请求）
// 数据模拟：平安银行(000001) 近80个交易日，包含多个明确拐点

const SAMPLE_KLINES_DAY = [
  // 阶段1：底部盘整后启动 (1-15)
  { time:'2026-02-10', open:10.20, close:10.35, high:10.42, low:10.15, volume:185000, amount:1910000, amplitude:2.65, changePct:1.47, change:0.15, turnover:0.8 },
  { time:'2026-02-11', open:10.38, close:10.28, high:10.45, low:10.22, volume:162000, amount:1670000, amplitude:2.25, changePct:-0.68, change:-0.07, turnover:0.7 },
  { time:'2026-02-12', open:10.30, close:10.52, high:10.58, low:10.25, volume:210000, amount:2180000, amplitude:3.18, changePct:2.33, change:0.24, turnover:0.9 },
  { time:'2026-02-13', open:10.55, close:10.48, high:10.62, low:10.40, volume:178000, amount:1860000, amplitude:2.12, changePct:-0.76, change:-0.08, turnover:0.8 },
  { time:'2026-02-14', open:10.50, close:10.78, high:10.85, low:10.45, volume:245000, amount:2600000, amplitude:3.82, changePct:2.86, change:0.30, turnover:1.1 },

  // 阶段2：主升浪 — 连续上涨 (6-25)
  { time:'2026-02-17', open:10.80, close:11.05, high:11.12, low:10.75, volume:320000, amount:3480000, amplitude:3.43, changePct:2.50, change:0.27, turnover:1.4 },
  { time:'2026-02-18', open:11.10, close:11.42, high:11.50, low:11.05, volume:410000, amount:4600000, amplitude:4.07, changePct:3.35, change:0.37, turnover:1.8 },
  { time:'2026-02-19', open:11.45, close:11.38, high:11.55, low:11.30, volume:295000, amount:3360000, amplitude:2.21, changePct:-0.35, change:-0.04, turnover:1.3 },
  { time:'2026-02-20', open:11.40, close:11.72, high:11.78, low:11.35, volume:380000, amount:4380000, amplitude:3.78, changePct:2.99, change:0.34, turnover:1.6 },
  { time:'2026-02-21', open:11.75, close:11.95, high:12.05, low:11.70, volume:450000, amount:5320000, amplitude:2.99, changePct:1.96, change:0.23, turnover:2.0 },
  { time:'2026-02-24', open:12.00, close:12.18, high:12.22, low:11.90, volume:420000, amount:5050000, amplitude:2.69, changePct:1.92, change:0.23, turnover:1.8 },
  { time:'2026-02-25', open:12.20, close:12.45, high:12.52, low:12.15, volume:510000, amount:6260000, amplitude:3.04, changePct:2.22, change:0.27, turnover:2.2 },
  { time:'2026-02-26', open:12.50, close:12.35, high:12.58, low:12.28, volume:380000, amount:4700000, amplitude:2.44, changePct:-0.80, change:-0.10, turnover:1.6 },
  { time:'2026-02-27', open:12.38, close:12.68, high:12.75, low:12.32, volume:470000, amount:5860000, amplitude:3.48, changePct:2.67, change:0.33, turnover:2.0 },
  { time:'2026-02-28', open:12.70, close:12.88, high:12.95, low:12.65, volume:520000, amount:6620000, amplitude:2.37, changePct:1.58, change:0.20, turnover:2.3 },

  // 🔴 拐点1：主要顶部 (16) — 放量冲高回落，长上影
  { time:'2026-03-03', open:12.90, close:12.55, high:13.28, low:12.50, volume:680000, amount:8720000, amplitude:6.24, changePct:-2.71, change:-0.35, turnover:3.0 },

  // 阶段3：下跌段 (17-30)
  { time:'2026-03-04', open:12.50, close:12.22, high:12.58, low:12.15, volume:420000, amount:5160000, amplitude:3.52, changePct:-2.63, change:-0.33, turnover:1.8 },
  { time:'2026-03-05', open:12.20, close:12.05, high:12.28, low:11.95, volume:350000, amount:4220000, amplitude:2.74, changePct:-1.39, change:-0.17, turnover:1.5 },
  { time:'2026-03-06', open:12.08, close:11.88, high:12.12, low:11.80, volume:310000, amount:3690000, amplitude:2.68, changePct:-1.41, change:-0.17, turnover:1.3 },
  { time:'2026-03-07', open:11.85, close:12.02, high:12.08, low:11.78, volume:280000, amount:3330000, amplitude:2.54, changePct:1.18, change:0.14, turnover:1.2 },
  { time:'2026-03-10', open:12.05, close:11.82, high:12.10, low:11.75, volume:265000, amount:3140000, amplitude:2.94, changePct:-1.66, change:-0.20, turnover:1.1 },
  { time:'2026-03-11', open:11.80, close:11.55, high:11.85, low:11.48, volume:310000, amount:3590000, amplitude:3.18, changePct:-2.28, change:-0.27, turnover:1.3 },
  { time:'2026-03-12', open:11.52, close:11.35, high:11.58, low:11.28, volume:290000, amount:3300000, amplitude:2.63, changePct:-1.73, change:-0.20, turnover:1.2 },
  { time:'2026-03-13', open:11.32, close:11.42, high:11.48, low:11.22, volume:240000, amount:2720000, amplitude:2.32, changePct:0.62, change:0.07, turnover:1.0 },
  { time:'2026-03-14', open:11.45, close:11.28, high:11.50, low:11.20, volume:225000, amount:2540000, amplitude:2.65, changePct:-1.23, change:-0.14, turnover:1.0 },

  // 🟢 拐点2：主要底部 (26) — 缩量止跌，长下影
  { time:'2026-03-17', open:11.25, close:10.88, high:11.28, low:10.72, volume:350000, amount:3820000, amplitude:5.15, changePct:-3.55, change:-0.40, turnover:1.5 },

  // 阶段4：反弹修复 (27-42)
  { time:'2026-03-18', open:10.90, close:11.15, high:11.20, low:10.85, volume:380000, amount:4170000, amplitude:3.22, changePct:2.48, change:0.27, turnover:1.6 },
  { time:'2026-03-19', open:11.18, close:11.42, high:11.48, low:11.12, volume:420000, amount:4720000, amplitude:3.24, changePct:2.42, change:0.27, turnover:1.8 },
  { time:'2026-03-20', open:11.45, close:11.35, high:11.52, low:11.28, volume:310000, amount:3520000, amplitude:2.12, changePct:-0.61, change:-0.07, turnover:1.3 },
  { time:'2026-03-21', open:11.38, close:11.58, high:11.65, low:11.32, volume:360000, amount:4110000, amplitude:2.91, changePct:2.03, change:0.23, turnover:1.5 },
  { time:'2026-03-24', open:11.60, close:11.78, high:11.82, low:11.55, volume:390000, amount:4540000, amplitude:2.34, changePct:1.73, change:0.20, turnover:1.7 },
  { time:'2026-03-25', open:11.80, close:11.95, high:12.02, low:11.75, volume:430000, amount:5080000, amplitude:2.30, changePct:1.44, change:0.17, turnover:1.9 },
  { time:'2026-03-26', open:12.00, close:11.82, high:12.05, low:11.78, volume:350000, amount:4150000, amplitude:2.28, changePct:-1.09, change:-0.13, turnover:1.5 },
  { time:'2026-03-27', open:11.85, close:12.08, high:12.12, low:11.80, volume:370000, amount:4400000, amplitude:2.71, changePct:2.20, change:0.26, turnover:1.6 },
  { time:'2026-03-28', open:12.10, close:12.25, high:12.30, low:12.05, volume:400000, amount:4850000, amplitude:2.07, changePct:1.41, change:0.17, turnover:1.7 },

  // 🔴 拐点3：阶段高点 (37) — 反弹遇阻，放量滞涨
  { time:'2026-03-31', open:12.28, close:12.05, high:12.45, low:12.00, volume:520000, amount:6320000, amplitude:3.72, changePct:-1.63, change:-0.20, turnover:2.3 },

  // 阶段5：二次探底 (38-50)
  { time:'2026-04-01', open:12.02, close:11.78, high:12.08, low:11.72, volume:380000, amount:4490000, amplitude:3.03, changePct:-2.24, change:-0.27, turnover:1.6 },
  { time:'2026-04-02', open:11.75, close:11.55, high:11.80, low:11.48, volume:340000, amount:3940000, amplitude:2.75, changePct:-1.95, change:-0.23, turnover:1.5 },
  { time:'2026-04-03', open:11.52, close:11.62, high:11.68, low:11.42, volume:280000, amount:3220000, amplitude:2.27, changePct:0.61, change:0.07, turnover:1.2 },
  { time:'2026-04-07', open:11.65, close:11.45, high:11.68, low:11.38, volume:260000, amount:2980000, amplitude:2.61, changePct:-1.46, change:-0.17, turnover:1.1 },
  { time:'2026-04-08', open:11.42, close:11.28, high:11.48, low:11.20, volume:290000, amount:3270000, amplitude:2.47, changePct:-1.48, change:-0.17, turnover:1.2 },

  // 🟢 拐点4：主要底部 (43) — 缩量至地量，锤子线
  { time:'2026-04-09', open:11.25, close:11.05, high:11.28, low:10.88, volume:420000, amount:4620000, amplitude:3.62, changePct:-2.04, change:-0.23, turnover:1.8 },

  // 阶段6：主升浪 (44-62)
  { time:'2026-04-10', open:11.08, close:11.32, high:11.38, low:11.02, volume:380000, amount:4230000, amplitude:3.26, changePct:2.44, change:0.27, turnover:1.6 },
  { time:'2026-04-11', open:11.35, close:11.55, high:11.60, low:11.30, volume:410000, amount:4670000, amplitude:2.65, changePct:2.03, change:0.23, turnover:1.8 },
  { time:'2026-04-14', open:11.58, close:11.78, high:11.85, low:11.52, volume:450000, amount:5230000, amplitude:2.87, changePct:1.99, change:0.23, turnover:2.0 },
  { time:'2026-04-15', open:11.80, close:11.95, high:12.02, low:11.75, volume:430000, amount:5080000, amplitude:2.30, changePct:1.44, change:0.17, turnover:1.9 },
  { time:'2026-04-16', open:12.00, close:12.22, high:12.28, low:11.95, volume:480000, amount:5780000, amplitude:2.76, changePct:2.26, change:0.27, turnover:2.1 },
  { time:'2026-04-17', open:12.25, close:12.08, high:12.30, low:12.02, volume:360000, amount:4360000, amplitude:2.31, changePct:-1.15, change:-0.14, turnover:1.6 },
  { time:'2026-04-18', open:12.10, close:12.35, high:12.40, low:12.05, volume:420000, amount:5100000, amplitude:2.90, changePct:2.24, change:0.27, turnover:1.8 },
  { time:'2026-04-21', open:12.38, close:12.55, high:12.62, low:12.32, volume:460000, amount:5700000, amplitude:2.44, changePct:1.62, change:0.20, turnover:2.0 },
  { time:'2026-04-22', open:12.58, close:12.78, high:12.85, low:12.52, volume:500000, amount:6310000, amplitude:2.65, changePct:1.83, change:0.23, turnover:2.2 },
  { time:'2026-04-23', open:12.80, close:12.72, high:12.88, low:12.65, volume:390000, amount:4950000, amplitude:1.82, changePct:-0.47, change:-0.06, turnover:1.7 },
  { time:'2026-04-24', open:12.75, close:12.95, high:13.02, low:12.70, volume:470000, amount:6010000, amplitude:2.52, changePct:1.81, change:0.23, turnover:2.1 },
  { time:'2026-04-25', open:12.98, close:13.18, high:13.25, low:12.92, volume:530000, amount:6890000, amplitude:2.55, changePct:1.78, change:0.23, turnover:2.3 },

  // 🔴 拐点5：主要顶部 (57) — 天量见顶，阴包阳
  { time:'2026-04-28', open:13.20, close:12.72, high:13.42, low:12.68, volume:720000, amount:9330000, amplitude:5.68, changePct:-3.49, change:-0.46, turnover:3.2 },

  // 阶段7：快速下跌 (58-68)
  { time:'2026-04-29', open:12.70, close:12.35, high:12.75, low:12.28, volume:480000, amount:5960000, amplitude:3.76, changePct:-2.91, change:-0.37, turnover:2.1 },
  { time:'2026-04-30', open:12.32, close:12.08, high:12.38, low:12.00, volume:410000, amount:4970000, amplitude:3.12, changePct:-2.19, change:-0.27, turnover:1.8 },
  { time:'2026-05-05', open:12.05, close:11.85, high:12.10, low:11.78, volume:380000, amount:4510000, amplitude:2.68, changePct:-1.90, change:-0.23, turnover:1.6 },
  { time:'2026-05-06', open:11.82, close:11.65, high:11.88, low:11.58, volume:340000, amount:3960000, amplitude:2.56, changePct:-1.69, change:-0.20, turnover:1.5 },
  { time:'2026-05-07', open:11.62, close:11.78, high:11.82, low:11.55, volume:290000, amount:3380000, amplitude:2.31, changePct:1.12, change:0.13, turnover:1.3 },
  { time:'2026-05-08', open:11.80, close:11.58, high:11.85, low:11.52, volume:310000, amount:3600000, amplitude:2.82, changePct:-1.70, change:-0.20, turnover:1.3 },
  { time:'2026-05-09', open:11.55, close:11.32, high:11.60, low:11.25, volume:330000, amount:3750000, amplitude:3.07, changePct:-2.25, change:-0.26, turnover:1.4 },

  // 🟢 拐点6：阶段低点 (65) — 长下影缩量止跌
  { time:'2026-05-12', open:11.30, close:11.05, high:11.32, low:10.92, volume:370000, amount:4080000, amplitude:3.59, changePct:-2.39, change:-0.27, turnover:1.6 },

  // 阶段8：震荡筑底反弹 (66-80)
  { time:'2026-05-13', open:11.08, close:11.22, high:11.28, low:11.02, volume:320000, amount:3550000, amplitude:2.36, changePct:1.54, change:0.17, turnover:1.4 },
  { time:'2026-05-14', open:11.25, close:11.15, high:11.30, low:11.08, volume:270000, amount:3000000, amplitude:1.98, changePct:-0.62, change:-0.07, turnover:1.2 },
  { time:'2026-05-15', open:11.18, close:11.38, high:11.42, low:11.12, volume:310000, amount:3470000, amplitude:2.70, changePct:2.06, change:0.23, turnover:1.3 },
  { time:'2026-05-16', open:11.40, close:11.52, high:11.58, low:11.35, volume:340000, amount:3880000, amplitude:2.02, changePct:1.23, change:0.14, turnover:1.5 },
  { time:'2026-05-19', open:11.55, close:11.42, high:11.60, low:11.35, volume:280000, amount:3190000, amplitude:2.19, changePct:-0.87, change:-0.10, turnover:1.2 },
  { time:'2026-05-20', open:11.45, close:11.65, high:11.70, low:11.40, volume:360000, amount:4130000, amplitude:2.63, changePct:2.01, change:0.23, turnover:1.6 },
  { time:'2026-05-21', open:11.68, close:11.82, high:11.88, low:11.62, volume:390000, amount:4550000, amplitude:2.24, changePct:1.46, change:0.17, turnover:1.7 },
  { time:'2026-05-22', open:11.85, close:11.78, high:11.90, low:11.72, volume:320000, amount:3760000, amplitude:1.54, changePct:-0.34, change:-0.04, turnover:1.4 },
  { time:'2026-05-23', open:11.80, close:11.95, high:12.00, low:11.75, volume:370000, amount:4370000, amplitude:2.13, changePct:1.44, change:0.17, turnover:1.6 },
  { time:'2026-05-26', open:11.98, close:11.88, high:12.05, low:11.82, volume:330000, amount:3910000, amplitude:1.94, changePct:-0.59, change:-0.07, turnover:1.4 },
  { time:'2026-05-27', open:11.90, close:12.08, high:12.12, low:11.85, volume:380000, amount:4530000, amplitude:2.28, changePct:1.68, change:0.20, turnover:1.6 },
  { time:'2026-05-28', open:12.10, close:11.95, high:12.15, low:11.90, volume:350000, amount:4180000, amplitude:2.08, changePct:-1.08, change:-0.13, turnover:1.5 },
  { time:'2026-05-29', open:11.98, close:12.15, high:12.22, low:11.92, volume:400000, amount:4800000, amplitude:2.52, changePct:1.67, change:0.20, turnover:1.7 },
  { time:'2026-05-30', open:12.18, close:12.28, high:12.35, low:12.12, volume:420000, amount:5110000, amplitude:1.90, changePct:1.07, change:0.13, turnover:1.8 },
];

// 5分钟数据：取最近1天的日内走势（简化版，约48根5分钟K线）
const SAMPLE_KLINES_5MIN = [
  { time:'2026-05-30 09:35', open:12.18, close:12.22, high:12.25, low:12.16, volume:45000, amount:548000, amplitude:0.74, changePct:0.33, change:0.04, turnover:0.2 },
  { time:'2026-05-30 09:40', open:12.23, close:12.20, high:12.26, low:12.18, volume:38000, amount:463000, amplitude:0.66, changePct:-0.16, change:-0.02, turnover:0.2 },
  { time:'2026-05-30 09:45', open:12.21, close:12.28, high:12.30, low:12.19, volume:52000, amount:635000, amplitude:0.90, changePct:0.66, change:0.08, turnover:0.2 },
  { time:'2026-05-30 09:50', open:12.29, close:12.35, high:12.38, low:12.26, volume:61000, amount:749000, amplitude:0.98, changePct:0.57, change:0.07, turnover:0.3 },
  { time:'2026-05-30 09:55', open:12.36, close:12.32, high:12.40, low:12.30, volume:48000, amount:591000, amplitude:0.81, changePct:-0.24, change:-0.03, turnover:0.2 },
  { time:'2026-05-30 10:00', open:12.33, close:12.42, high:12.45, low:12.31, volume:55000, amount:678000, amplitude:1.14, changePct:0.81, change:0.10, turnover:0.2 },
  { time:'2026-05-30 10:05', open:12.43, close:12.38, high:12.46, low:12.35, volume:42000, amount:519000, amplitude:0.89, changePct:-0.32, change:-0.04, turnover:0.2 },
  { time:'2026-05-30 10:10', open:12.39, close:12.45, high:12.48, low:12.37, volume:50000, amount:619000, amplitude:0.89, changePct:0.57, change:0.07, turnover:0.2 },
  { time:'2026-05-30 10:15', open:12.46, close:12.50, high:12.55, low:12.44, volume:58000, amount:722000, amplitude:0.88, changePct:0.40, change:0.05, turnover:0.3 },
  { time:'2026-05-30 10:20', open:12.51, close:12.42, high:12.54, low:12.40, volume:43000, amount:534000, amplitude:1.12, changePct:-0.64, change:-0.08, turnover:0.2 },
  { time:'2026-05-30 10:25', open:12.41, close:12.38, high:12.44, low:12.35, volume:36000, amount:445000, amplitude:0.73, changePct:-0.32, change:-0.04, turnover:0.2 },
  { time:'2026-05-30 10:30', open:12.37, close:12.28, high:12.39, low:12.25, volume:40000, amount:491000, amplitude:1.13, changePct:-0.81, change:-0.10, turnover:0.2 },
  { time:'2026-05-30 10:35', open:12.27, close:12.32, high:12.34, low:12.24, volume:35000, amount:429000, amplitude:0.82, changePct:0.33, change:0.04, turnover:0.2 },
  { time:'2026-05-30 10:40', open:12.33, close:12.25, high:12.35, low:12.22, volume:38000, amount:465000, amplitude:1.06, changePct:-0.57, change:-0.07, turnover:0.2 },
  { time:'2026-05-30 10:45', open:12.24, close:12.18, high:12.26, low:12.15, volume:44000, amount:535000, amplitude:0.90, changePct:-0.57, change:-0.07, turnover:0.2 },
  { time:'2026-05-30 10:50', open:12.17, close:12.22, high:12.25, low:12.14, volume:39000, amount:474000, amplitude:0.90, changePct:0.58, change:0.07, turnover:0.2 },
  { time:'2026-05-30 10:55', open:12.23, close:12.20, high:12.26, low:12.17, volume:34000, amount:414000, amplitude:0.74, changePct:-0.16, change:-0.02, turnover:0.1 },
  { time:'2026-05-30 11:00', open:12.19, close:12.12, high:12.22, low:12.10, volume:46000, amount:557000, amplitude:0.98, changePct:-0.66, change:-0.08, turnover:0.2 },
  { time:'2026-05-30 11:05', open:12.11, close:12.15, high:12.18, low:12.08, volume:37000, amount:447000, amplitude:0.83, changePct:0.25, change:0.03, turnover:0.2 },
  { time:'2026-05-30 11:10', open:12.16, close:12.10, high:12.18, low:12.08, volume:32000, amount:387000, amplitude:0.82, changePct:-0.41, change:-0.05, turnover:0.1 },
  { time:'2026-05-30 11:15', open:12.09, close:12.05, high:12.12, low:12.02, volume:41000, amount:493000, amplitude:0.83, changePct:-0.41, change:-0.05, turnover:0.2 },
  { time:'2026-05-30 11:20', open:12.04, close:12.08, high:12.10, low:12.01, volume:36000, amount:433000, amplitude:0.75, changePct:0.25, change:0.03, turnover:0.2 },
  { time:'2026-05-30 11:25', open:12.09, close:12.06, high:12.11, low:12.04, volume:28000, amount:337000, amplitude:0.58, changePct:-0.17, change:-0.02, turnover:0.1 },
  { time:'2026-05-30 11:30', open:12.05, close:12.10, high:12.12, low:12.04, volume:33000, amount:397000, amplitude:0.66, changePct:0.33, change:0.04, turnover:0.1 },
  { time:'2026-05-30 13:05', open:12.11, close:12.20, high:12.22, low:12.09, volume:52000, amount:630000, amplitude:1.07, changePct:0.83, change:0.10, turnover:0.2 },
  { time:'2026-05-30 13:10', open:12.21, close:12.28, high:12.30, low:12.18, volume:58000, amount:707000, amplitude:0.98, changePct:0.66, change:0.08, turnover:0.3 },
  { time:'2026-05-30 13:15', open:12.29, close:12.22, high:12.32, low:12.20, volume:45000, amount:549000, amplitude:0.98, changePct:-0.49, change:-0.06, turnover:0.2 },
  { time:'2026-05-30 13:20', open:12.23, close:12.25, high:12.28, low:12.20, volume:38000, amount:463000, amplitude:0.66, changePct:0.25, change:0.03, turnover:0.2 },
  { time:'2026-05-30 13:25', open:12.26, close:12.22, high:12.28, low:12.19, volume:35000, amount:426000, amplitude:0.74, changePct:-0.24, change:-0.03, turnover:0.2 },
  { time:'2026-05-30 13:30', open:12.21, close:12.18, high:12.24, low:12.15, volume:42000, amount:510000, amplitude:0.74, changePct:-0.33, change:-0.04, turnover:0.2 },
  { time:'2026-05-30 13:35', open:12.17, close:12.12, high:12.20, low:12.10, volume:39000, amount:472000, amplitude:0.82, changePct:-0.49, change:-0.06, turnover:0.2 },
  { time:'2026-05-30 13:40', open:12.11, close:12.08, high:12.14, low:12.05, volume:36000, amount:434000, amplitude:0.74, changePct:-0.33, change:-0.04, turnover:0.2 },
  { time:'2026-05-30 13:45', open:12.07, close:12.15, high:12.18, low:12.05, volume:42000, amount:507000, amplitude:1.07, changePct:0.58, change:0.07, turnover:0.2 },
  { time:'2026-05-30 13:50', open:12.16, close:12.20, high:12.22, low:12.14, volume:38000, amount:461000, amplitude:0.66, changePct:0.41, change:0.05, turnover:0.2 },
  { time:'2026-05-30 13:55', open:12.21, close:12.18, high:12.24, low:12.15, volume:34000, amount:413000, amplitude:0.74, changePct:-0.16, change:-0.02, turnover:0.1 },
  { time:'2026-05-30 14:00', open:12.17, close:12.25, high:12.28, low:12.15, volume:48000, amount:584000, amplitude:1.07, changePct:0.57, change:0.07, turnover:0.2 },
  { time:'2026-05-30 14:05', open:12.26, close:12.22, high:12.30, low:12.20, volume:40000, amount:488000, amplitude:0.82, changePct:-0.24, change:-0.03, turnover:0.2 },
  { time:'2026-05-30 14:10', open:12.23, close:12.28, high:12.32, low:12.21, volume:45000, amount:549000, amplitude:0.90, changePct:0.49, change:0.06, turnover:0.2 },
  { time:'2026-05-30 14:15', open:12.29, close:12.35, high:12.38, low:12.26, volume:52000, amount:638000, amplitude:0.98, changePct:0.57, change:0.07, turnover:0.2 },
  { time:'2026-05-30 14:20', open:12.36, close:12.30, high:12.40, low:12.28, volume:43000, amount:528000, amplitude:0.97, changePct:-0.40, change:-0.05, turnover:0.2 },
  { time:'2026-05-30 14:25', open:12.31, close:12.38, high:12.42, low:12.28, volume:48000, amount:590000, amplitude:1.14, changePct:0.65, change:0.08, turnover:0.2 },
  { time:'2026-05-30 14:30', open:12.39, close:12.35, high:12.44, low:12.32, volume:41000, amount:505000, amplitude:0.97, changePct:-0.24, change:-0.03, turnover:0.2 },
  { time:'2026-05-30 14:35', open:12.36, close:12.32, high:12.38, low:12.28, volume:37000, amount:454000, amplitude:0.81, changePct:-0.24, change:-0.03, turnover:0.2 },
  { time:'2026-05-30 14:40', open:12.33, close:12.28, high:12.35, low:12.25, volume:38000, amount:465000, amplitude:0.81, changePct:-0.32, change:-0.04, turnover:0.2 },
  { time:'2026-05-30 14:45', open:12.27, close:12.22, high:12.30, low:12.20, volume:35000, amount:427000, amplitude:0.82, changePct:-0.49, change:-0.06, turnover:0.2 },
  { time:'2026-05-30 14:50', open:12.21, close:12.25, high:12.28, low:12.18, volume:42000, amount:512000, amplitude:0.82, changePct:0.25, change:0.03, turnover:0.2 },
  { time:'2026-05-30 14:55', open:12.26, close:12.20, high:12.28, low:12.17, volume:38000, amount:462000, amplitude:0.90, changePct:-0.41, change:-0.05, turnover:0.2 },
  { time:'2026-05-30 15:00', open:12.19, close:12.28, high:12.30, low:12.17, volume:55000, amount:670000, amplitude:1.07, changePct:0.66, change:0.08, turnover:0.2 },
];

// 根据周期返回对应的示例数据
function getSampleKlines(stockCode, period) {
  let klines;
  if (period === 'day' || period === 'week' || period === 'month') {
    klines = SAMPLE_KLINES_DAY;
  } else {
    klines = SAMPLE_KLINES_5MIN;
  }

  return {
    code: stockCode || '000001',
    name: '平安银行',
    secid: '0.000001',
    klines: klines,
    count: klines.length,
    latest: klines[klines.length - 1],
  };
}

// 模拟实时报价
function getSampleQuote(stockCode) {
  const latest = SAMPLE_KLINES_DAY[SAMPLE_KLINES_DAY.length - 1];
  const prev = SAMPLE_KLINES_DAY[SAMPLE_KLINES_DAY.length - 2];
  const change = latest.close - prev.close;
  const changePct = (change / prev.close * 100);

  return {
    code: stockCode || '000001',
    name: '平安银行',
    price: latest.close,
    high: latest.high,
    low: latest.low,
    open: latest.open,
    volume: latest.volume,
    amount: latest.amount,
    change: change,
    changePct: changePct,
    turnover: latest.turnover,
    pe: 5.8,
    totalValue: 238000000000,
    flowValue: 215000000000,
  };
}

// 模拟搜索
function searchSampleStocks(keyword) {
  const DB = [
    { code: '000001', name: '平安银行', market: 'sz', type: 'A' },
    { code: '000002', name: '万科A', market: 'sz', type: 'A' },
    { code: '000858', name: '五粮液', market: 'sz', type: 'A' },
    { code: '600519', name: '贵州茅台', market: 'sh', type: 'A' },
    { code: '601318', name: '中国平安', market: 'sh', type: 'A' },
    { code: '600036', name: '招商银行', market: 'sh', type: 'A' },
    { code: '300750', name: '宁德时代', market: 'sz', type: 'A' },
    { code: '002594', name: '比亚迪', market: 'sz', type: 'A' },
  ];

  if (!keyword) return [];
  const kw = keyword.toUpperCase();
  return DB.filter(s =>
    s.code.includes(kw) || s.name.includes(kw) || s.name.includes(keyword)
  );
}

module.exports = {
  getSampleKlines,
  getSampleQuote,
  searchSampleStocks,
  SAMPLE_KLINES_DAY,
  SAMPLE_KLINES_5MIN,
};
