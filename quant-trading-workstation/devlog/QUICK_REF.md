# 🗺️ 开发路线图速查

> 一句话了解当前在哪、下一步做什么

---

## 📍 当前位置

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9
   ✅      ✅       ✅       🚧       🚧
  已完成  已完成  已完成  骨架完成  骨架完成
```

---

## 🔜 下次开发做什么

1. **Phase 3 智能选股**: 实现基本面过滤 + 技术面筛选核心逻辑，多因子打分
2. **Phase 4 策略回测**: 完善向量化引擎，接入真实数据验证
3. **前后端联调**: 启动 Electron 应用进行完整功能测试

---

## 🎯 本周目标 (6/9 - 6/15)

- [x] Phase 0 基础设施完成
- [x] Phase 1 行情看盘完成 (多周期K线 + 实时行情 + 技术指标)
- [x] Phase 2 缠论引擎完成 (分型→笔→线段→中枢→买卖点 + 多维度分析)
- [ ] Phase 3 智能选股核心逻辑
- [ ] Phase 4 回测引擎完善

---

## 📂 常用文件速查

| 用途 | 文件 |
|------|------|
| 项目概览 | [README.md](../README.md) |
| 架构设计 | [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) |
| 完整任务清单 | [docs/TASK_LIST.md](../docs/TASK_LIST.md) |
| 数据源方案 | [docs/DATA_SOURCES.md](../docs/DATA_SOURCES.md) |
| 算法说明 | [docs/ALGORITHMS.md](../docs/ALGORITHMS.md) |
| 技术决策 | [devlog/DECISIONS.md](DECISIONS.md) |
| 问题记录 | [devlog/ISSUES.md](ISSUES.md) |

---

## 🔗 与现有项目的关系

- 本项目 `quant-trading-workstation/` 是**量化交易工具**（行情+选股+回测+缠论）
- 已有项目 `ai-stock-learning/` 是**股票学习小程序**（知识+AI导师+模拟交易）
- 两者定位不同，但知识库 `knowledge-base/` 可互相参考（尤其是缠论部分）
