// AI分析页 — 对接Python引擎 + 本地降级
const app = getApp();
const aiEngine = require('../../services/ai-engine');
const marketData = require('../../services/market-data');
const turningPoints = require('../../utils/turning-points');

Page({
  data: {
    stockName: '--',
    stockCode: '--',
    period: 'day',
    latestPrice: 0,
    latestChange: 0,

    // 分析状态
    analysisLoading: true,
    engineOnline: false,       // Python引擎是否在线
    analysisSource: 'local',   // 'engine' | 'local'

    // 分析结果
    aiAnalysis: null,

    // 拐点上下文（从行情页跳转时带入）
    point: null,
    pointSelected: false,

    // 错误状态
    error: null,
  },

  onLoad() {
    // 从全局获取当前股票
    const stock = app.globalData.currentStock;
    if (stock && stock.code) {
      this.setData({
        stockCode: stock.code,
        stockName: stock.name || stock.code,
      });
    }
  },

  onShow() {
    const stock = app.globalData.currentStock;
    if (!stock || !stock.code) {
      this.setData({
        analysisLoading: false,
        aiAnalysis: {
          title: '未选择股票',
          summary: '请先在行情页选择一只股票，再切换到本页查看AI分析。',
          signals: [],
          conclusion: ''
        }
      });
      return;
    }

    // 更新股票信息
    const code = stock.code;
    this.setData({
      stockCode: code,
      stockName: stock.name || code,
    });

    // 检查是否有选中的拐点
    const ctx = app.globalData.currentAnalysis;
    if (ctx && ctx.point) {
      this.setData({
        point: ctx.point,
        pointSelected: true,
      });
    }

    // 开始分析
    this.runAnalysis(code);
  },

  // 执行分析：优先Python引擎，失败降级本地
  async runAnalysis(code) {
    this.setData({ analysisLoading: true, error: null });

    // 先ping引擎
    const health = await aiEngine.ping();

    if (health.online) {
      console.log('[分析页] Python引擎在线, strategies:', health.strategies.length,
                  'predictors:', health.predictors.length);
      try {
        // 从小程序端获取K线数据（wx.request能正常访问东方财富API）
        const period = this.data.period || 'day';
        console.log('[分析页] 小程序端获取K线数据...');
        const klineResult = await marketData.fetchKlineData(code, period, 200);
        const klines = klineResult.klines || [];
        const stockName = klineResult.name || '';
        const latestPrice = klineResult.latest ? klineResult.latest.close : 0;
        const latestChangePct = klineResult.latest ? klineResult.latest.changePct : 0;

        console.log('[分析页] K线数据获取成功:', klines.length, '条, 发送到Python引擎分析...');

        // 发送K线数据到Python引擎分析
        const report = await aiEngine.fetchAnalysisWithData({
          code: code,
          period: period,
          klines: klines,
          stockName: stockName,
          latestPrice: latestPrice,
          latestChangePct: latestChangePct,
        });

        this.setData({
          engineOnline: true,
          analysisSource: 'engine',
          analysisLoading: false,
          latestPrice: report.meta.latest_price,
          latestChange: report.meta.latest_change_pct,
          aiAnalysis: this.formatEngineReport(report),
        });
        // 保存到历史
        this.saveToHistory(code, report.meta.stock_name, '深度AI分析');
        return;
      } catch (err) {
        console.warn('[分析页] 引擎调用失败，尝试直接API...', err.message);
        // 回退：让Python引擎自己获取数据（如果网络允许）
        try {
          const report = await aiEngine.fetchAnalysis({
            code: code,
            period: this.data.period || 'day',
            count: 200,
          });
          this.setData({
            engineOnline: true,
            analysisSource: 'engine',
            analysisLoading: false,
            latestPrice: report.meta.latest_price,
            latestChange: report.meta.latest_change_pct,
            aiAnalysis: this.formatEngineReport(report),
          });
          this.saveToHistory(code, report.meta.stock_name, '深度AI分析');
          return;
        } catch (err2) {
          console.warn('[分析页] 直接API也失败，降级到本地分析:', err2.message);
        }
      }
    }

    // 降级到本地分析
    this.setData({ engineOnline: false, analysisSource: 'local' });
    this.runLocalAnalysis(code);
  },

  // 本地分析（降级方案，复用原有拐点分析逻辑）
  runLocalAnalysis(code) {
    const ctx = app.globalData.currentAnalysis;
    if (!ctx || !ctx.point) {
      // 没有拐点上下文，做个简单分析
      this.setData({
        analysisLoading: false,
        aiAnalysis: {
          title: `AI引擎离线 · ${code} 基础分析`,
          summary: 'Python AI引擎未启动，仅展示基础数据。启动方式：\n\ncd ai-engine && python server.py',
          details: [],
          signals: [{
            icon: '💡',
            text: '启动 Python 引擎后可获得：技术指标分析、K线形态识别、趋势判断、风险评估等深度分析',
            type: 'info'
          }],
          conclusion: '请在终端运行 python server.py 启动AI分析引擎，获得完整分析能力。',
          disclaimer: '本地模式仅提供基础展示，完整分析需要Python引擎支持。',
        }
      });
      return;
    }

    // 有拐点上下文，用本地算法分析
    const { point, context, klines } = ctx;
    const analysis = this.buildLocalAnalysis(point, context, klines);

    this.setData({
      analysisLoading: false,
      aiAnalysis: analysis,
      latestPrice: point.price || 0,
      latestChange: point.changeFromPrev || 0,
    });

    this.saveToHistory(code, ctx.stockName, analysis.title);
  },

  // 格式化引擎报告为页面展示结构
  formatEngineReport(report) {
    const s = report.summary;
    const p = report.patterns;
    const risk = report.risk;

    // 汇总信号
    const signals = [];
    s.bullish_signals.forEach(text => {
      signals.push({ icon: '🟢', text, type: 'positive' });
    });
    s.bearish_signals.forEach(text => {
      signals.push({ icon: '🔴', text, type: 'warning' });
    });

    // 指标状态信号
    const rsiStatus = s.rsi_status;
    if (rsiStatus.rsi14 !== null) {
      if (rsiStatus.rsi14 > 70) {
        signals.push({ icon: '⚠️', text: `RSI=${rsiStatus.rsi14} 超买区间，注意回调风险`, type: 'warning' });
      } else if (rsiStatus.rsi14 < 30) {
        signals.push({ icon: '🎯', text: `RSI=${rsiStatus.rsi14} 超卖区间，关注反弹机会`, type: 'positive' });
      }
    }

    const macdStatus = s.macd_status;
    if (macdStatus.signal === 'bullish') {
      signals.push({ icon: '📈', text: 'MACD多头排列，趋势偏强', type: 'positive' });
    } else if (macdStatus.signal === 'bearish') {
      signals.push({ icon: '📉', text: 'MACD空头排列，趋势偏弱', type: 'warning' });
    }

    // 风险信号
    risk.warnings.forEach(w => {
      const icon = w.level === 'high' ? '🔴' : w.level === 'medium' ? '🟡' : '🟢';
      signals.push({ icon, text: w.msg, type: w.level === 'high' ? 'warning' : 'info' });
    });

    // 没有信号时的默认
    if (signals.length === 0) {
      signals.push({ icon: '⚪', text: '当前无明显交易信号，观望为主', type: 'info' });
    }

    // 详情列表
    const details = [
      { label: '综合评分', value: `${s.score}/100 (${s.bias === 'bullish' ? '偏多' : s.bias === 'bearish' ? '偏空' : '中性'})` },
      { label: '整体趋势', value: p.trend.overall },
      { label: '均线排列', value: s.ma_status.arrangement },
      { label: 'MA5', value: s.ma_status.ma5 != null ? s.ma_status.ma5.toFixed(2) : '--' },
      { label: 'MA10', value: s.ma_status.ma10 != null ? s.ma_status.ma10.toFixed(2) : '--' },
      { label: 'MA20', value: s.ma_status.ma20 != null ? s.ma_status.ma20.toFixed(2) : '--' },
      { label: 'MA60', value: s.ma_status.ma60 != null ? s.ma_status.ma60.toFixed(2) : '--' },
      { label: 'RSI(14)', value: rsiStatus.rsi14 != null ? `${rsiStatus.rsi14.toFixed(1)} [${rsiStatus.status}]` : '--' },
      { label: 'MACD', value: `DIF=${macdStatus.dif?.toFixed(3) || '--'} DEA=${macdStatus.dea?.toFixed(3) || '--'}` },
      { label: '最近支撑', value: s.levels.nearest_support != null ? `¥${s.levels.nearest_support}` : '--' },
      { label: '最近压力', value: s.levels.nearest_resistance != null ? `¥${s.levels.nearest_resistance}` : '--' },
      { label: '风险评估', value: risk.level === 'high' ? '高风险' : risk.level === 'medium' ? '中等风险' : '低风险' },
    ];

    // 策略结果
    const strategyResults = (report.strategy_results || []).map(sr => ({
      name: sr.strategy,
      signals: (sr.signals || []).map(sig => ({
        label: sig.type === 'buy' ? '买入' : sig.type === 'sell' ? '卖出' : '持有',
        value: `¥${sig.price} 强度${sig.strength}/10 ${sig.reason}`,
        type: sig.type === 'buy' ? 'positive' : sig.type === 'sell' ? 'warning' : 'info',
      })),
      confidence: sr.confidence,
      reason: sr.reason,
    }));

    // 预测结果
    const predictionResults = (report.prediction_results || []).map(pr => ({
      name: pr.predictor,
      direction: pr.direction === 'up' ? '📈 看涨' : pr.direction === 'down' ? '📉 看跌' : '➖ 横盘',
      confidence: pr.confidence,
      horizon: pr.horizon,
      target: pr.target_price,
      reason: pr.reason,
    }));

    // 结论
    const biasText = s.bias === 'bullish' ? '偏多' : s.bias === 'bearish' ? '偏空' : '中性';
    const conclusion = [
      `「${report.meta.stock_name || report.meta.code}」${report.meta.period_label}综合分析：`,
      `趋势${p.trend.overall}，综合评分 ${s.score}/100（${biasText}）。`,
      s.ma_status.arrangement + '，',
      `RSI ${rsiStatus.status}，`,
      `MACD ${macdStatus.signal === 'bullish' ? '偏多' : macdStatus.signal === 'bearish' ? '偏空' : '中性'}。`,
    ].join('');

    return {
      title: `${report.meta.stock_name || report.meta.code} AI深度分析`,
      summary: `${report.meta.period_label} · 评分${s.score}/100 · ${p.trend.overall} · ${risk.level === 'high' ? '高风险' : risk.level === 'medium' ? '中风险' : '低风险'}`,
      details,
      signals,
      strategyResults,
      predictionResults,
      conclusion,
      engineOnline: true,
      disclaimer: '⚠️ 以上分析由AI自动生成，仅供参考学习，不构成任何投资建议。实际交易请结合多方信息综合判断。',
    };
  },

  // 本地分析（降级方案）
  buildLocalAnalysis(point, context, klines) {
    const changeStr = point.changeFromPrev > 0
      ? `+${point.changeFromPrev}%` : `${point.changeFromPrev}%`;

    const signals = [];
    if (point.strength >= 7) {
      signals.push({
        icon: '🎯',
        text: `高强度${point.type === 'peak' ? '顶部' : '底部'}拐点（强度${point.strength}/10），反转概率较高`,
        type: 'strong',
      });
    }
    if (point.trendDays > 20) {
      signals.push({
        icon: '⏱️',
        text: `前期${point.trendBefore}持续${point.trendDays}天，拐点出现后趋势可能延续反转`,
        type: 'info',
      });
    }
    signals.push({
      icon: '💡',
      text: '启动Python引擎可获更深度分析：python server.py',
      type: 'info',
    });

    const conclusion = point.type === 'peak'
      ? `「${point.time}」在 ¥${point.price} 形成${point.label}。前段${point.trendBefore}${point.trendDays}天，涨幅${changeStr}。`
        + `建议结合量能变化和后续K线确认有效反转后再做决策。`
      : `「${point.time}」在 ¥${point.price} 形成${point.label}。前段${point.trendBefore}${point.trendDays}天，跌幅${changeStr}。`
        + `建议关注该位置是否形成有效支撑，等待右侧确认信号。`;

    return {
      title: `${point.label}分析（本地）`,
      summary: `${point.time} | ¥${point.price} | 强度 ${point.strength}/10 | 离线模式`,
      details: [
        { label: '拐点类型', value: point.label },
        { label: '发生时间', value: point.time },
        { label: '拐点价格', value: `¥${point.price}` },
        { label: '前段趋势', value: `${point.trendBefore} ${point.trendDays}天` },
        { label: '涨跌幅', value: changeStr },
        { label: '强度评分', value: `${point.strength}/10` },
      ],
      signals,
      conclusion: conclusion + '\n\n⚠️ 注意：当前为离线模式，启动Python引擎后可获得完整AI分析。',
      engineOnline: false,
      disclaimer: '⚠️ 以上分析由本地算法生成，仅供参考学习。启动 python server.py 获得AI深度分析。',
    };
  },

  // 保存分析历史
  saveToHistory(code, name, title) {
    const history = app.globalData.analysisHistory;
    history.unshift({
      time: new Date().toISOString(),
      stockCode: code,
      stockName: name,
      analysis: title,
      source: this.data.analysisSource,
    });
    app.globalData.analysisHistory = history.slice(0, 50);
    app.saveAnalysisHistory();
  },

  // 切换周期
  onPeriodChange(e) {
    const { period } = e.currentTarget.dataset;
    if (period === this.data.period) return;
    this.setData({ period });
    this.runAnalysis(this.data.stockCode);
  },

  // 重新分析
  onReanalyze() {
    this.setData({ pointSelected: false, point: null });
    this.runAnalysis(this.data.stockCode);
  },

  // 刷新引擎状态
  async onCheckEngine() {
    const health = await aiEngine.ping();
    if (health.online) {
      wx.showToast({ title: '引擎在线', icon: 'success' });
      this.runAnalysis(this.data.stockCode);
    } else {
      wx.showToast({ title: '引擎离线，请启动 python server.py', icon: 'none', duration: 3000 });
    }
  },
});
