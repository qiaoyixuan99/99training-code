// 行情页 - K线图表 + 拐点分析
const app = getApp();
const marketData = require('../../services/market-data');
const turningPoints = require('../../utils/turning-points');

Page({
  data: {
    statusBarHeight: 0,
    navBarHeight: 0,

    // 股票信息
    stockName: '--',
    stockCode: '000001',
    stockPrice: '0.00',
    stockChange: '0.00',
    stockChangePct: '0.00',
    isUp: true,

    // K线数据
    klines: [],
    turningPointList: [],
    keyLevels: { support: [], resistance: [] },

    // 当前周期
    periods: [
      { key: '5min', label: '5分' },
      { key: '15min', label: '15分' },
      { key: '30min', label: '30分' },
      { key: '60min', label: '60分' },
      { key: 'day', label: '日K' },
      { key: 'week', label: '周K' },
      { key: 'month', label: '月K' },
    ],
    activePeriod: 'day',

    // 搜索
    showSearch: false,
    searchKeyword: '',
    searchResults: [],

    // 图表渲染
    chartWidth: 0,
    chartHeight: 380,
    volumeHeight: 60,

    // 选中拐点
    selectedPoint: null,
    showPointDetail: false,

    // 十字线
    crosshair: null,

    // 加载状态
    loading: true,
    error: null,

    // Canvas就绪状态
    canvasReady: false,
  },

  // Canvas相关
  canvasCtx: null,
  canvasWidth: 0,
  canvasHeight: 0,
  dpr: 1,

  onLoad() {
    this.setData({
      statusBarHeight: app.globalData.statusBarHeight,
      navBarHeight: app.globalData.navBarHeight,
    });

    const stock = app.globalData.currentStock;
    if (stock && stock.code) {
      this.setData({
        stockCode: stock.code,
        stockName: stock.name || stock.code,
      });
    }

    // 加载数据（不依赖Canvas）
    this.loadData();
  },

  onReady() {
    // DOM就绪后才初始化Canvas
    this.initCanvas();
  },

  onShow() {
    const stock = app.globalData.currentStock;
    if (stock && stock.code && stock.code !== this.data.stockCode) {
      this.setData({
        stockCode: stock.code,
        stockName: stock.name || stock.code,
      });
      this.loadData();
    }
  },

  // 初始化Canvas（仅在onReady中调用）
  initCanvas() {
    console.log('[initCanvas] 开始获取Canvas节点...');

    // 先用默认查询（Page不需要.in(this)，但加.in(this)也兼容）
    const query = wx.createSelectorQuery();
    query.select('#klineCanvas')
      .fields({ node: true, size: true })
      .exec((res) => {
        console.log('[initCanvas] 查询结果:', JSON.stringify({
          hasRes: !!res,
          hasRes0: !!(res && res[0]),
          hasNode: !!(res && res[0] && res[0].node),
          width: res && res[0] ? res[0].width : 'N/A',
          height: res && res[0] ? res[0].height : 'N/A',
        }));

        if (!res || !res[0] || !res[0].node) {
          console.error('[initCanvas] Canvas节点获取失败，请确保基础库 >= 2.9.0');
          // 延迟重试一次（Canvas 2D节点可能有延迟）
          setTimeout(() => {
            console.log('[initCanvas] 延迟重试...');
            wx.createSelectorQuery().select('#klineCanvas')
              .fields({ node: true, size: true })
              .exec((retryRes) => {
                console.log('[initCanvas] 重试结果:', JSON.stringify({
                  hasNode: !!(retryRes && retryRes[0] && retryRes[0].node),
                  width: retryRes && retryRes[0] ? retryRes[0].width : 'N/A',
                  height: retryRes && retryRes[0] ? retryRes[0].height : 'N/A',
                }));
                if (retryRes && retryRes[0] && retryRes[0].node) {
                  this._setupCanvas(retryRes[0]);
                }
              });
          }, 300);
          return;
        }

        this._setupCanvas(res[0]);
      });
  },

  // 完成Canvas初始化（提取为独立方法）
  _setupCanvas(nodeInfo) {
    const canvas = nodeInfo.node;
    const ctx = canvas.getContext('2d');
    const dpr = wx.getSystemInfoSync().pixelRatio || 2;

    const width = nodeInfo.width;
    const height = nodeInfo.height;

    console.log(`[initCanvas] Canvas就绪: ${width}x${height}, dpr=${dpr}`);

    if (width === 0 || height === 0) {
      console.error('[initCanvas] Canvas尺寸为0，检查CSS/容器');
      return;
    }

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    this.canvasCtx = ctx;
    this.canvasWidth = width;
    this.canvasHeight = height;
    this.dpr = dpr;

    // 如果数据已就绪，立即绘制
    if (this.data.klines.length > 0) {
      console.log('[initCanvas] 数据已就绪，立即绘制');
      this.drawChart();
    } else {
      console.log('[initCanvas] 等待数据加载...');
    }
  },

  // 加载数据
  async loadData() {
    this.setData({ loading: true, error: null });

    try {
      const code = this.data.stockCode;
      const period = this.data.activePeriod;

      // 获取K线数据
      const klineResult = await marketData.fetchKlineData(code, period, 200);
      const klines = klineResult.klines;
      const stockName = klineResult.name || this.data.stockName;

      // 检测拐点
      const tpList = turningPoints.detectTurningPoints(klines, {
        lookback: 5,
        minDistance: 6,
      });

      // 找关键支撑/压力位
      const keyLevels = turningPoints.findKeyLevels(tpList, klines);

      // 获取实时报价
      let priceInfo = {};
      try {
        const quote = await marketData.fetchQuote(code);
        priceInfo = {
          stockPrice: quote.price.toFixed(2),
          stockChange: (quote.change >= 0 ? '+' : '') + quote.change.toFixed(2),
          stockChangePct: (quote.changePct >= 0 ? '+' : '') + quote.changePct.toFixed(2) + '%',
          isUp: quote.change >= 0,
        };
      } catch (e) {
        // 回退到K线最新数据
        const latest = klines[klines.length - 1];
        if (latest) {
          const change = latest.change || 0;
          priceInfo = {
            stockPrice: latest.close.toFixed(2),
            stockChange: (change >= 0 ? '+' : '') + change.toFixed(2),
            stockChangePct: (latest.changePct >= 0 ? '+' : '') + latest.changePct.toFixed(2) + '%',
            isUp: change >= 0,
          };
        }
      }

      this.setData({
        klines,
        turningPointList: tpList,
        keyLevels,
        stockName,
        ...priceInfo,
        loading: false,
        selectedPoint: null,
        showPointDetail: false,
      });

      // 如果Canvas已就绪，直接绘制
      console.log('[loadData] 数据加载完成, canvasCtx:', !!this.canvasCtx, ', klines:', klines.length);
      if (this.canvasCtx) {
        this.drawChart();
      } else {
        console.log('[loadData] Canvas未就绪，等待initCanvas触发绘制');
      }

    } catch (err) {
      console.error('加载K线数据失败:', err);
      this.setData({
        loading: false,
        error: err.message || '数据加载失败',
      });
    }
  },

  // 切换周期
  onPeriodChange(e) {
    const { period } = e.currentTarget.dataset;
    if (period === this.data.activePeriod) return;
    this.setData({ activePeriod: period });
    this.loadData();
  },

  // 搜索
  onSearchInput(e) {
    const keyword = e.detail.value;
    this.setData({ searchKeyword: keyword });

    if (keyword.length >= 2) {
      marketData.searchStock(keyword).then(results => {
        this.setData({ searchResults: results });
      }).catch(() => {});
    } else {
      this.setData({ searchResults: [] });
    }
  },

  onToggleSearch() {
    const willShow = !this.data.showSearch;
    this.setData({
      showSearch: willShow,
      searchKeyword: '',
      searchResults: [],
    });
    // 关闭搜索时，Canvas被wx:if重新创建，需要重新初始化
    if (!willShow) {
      this.canvasCtx = null;
      // 等待DOM更新后再初始化
      wx.nextTick(() => {
        this.initCanvas();
      });
    }
  },

  onSelectStock(e) {
    const { code, name } = e.currentTarget.dataset;
    if (!code) return;
    const stock = {
      code: code,
      name: name || code,
      market: code.startsWith('6') ? 'sh' : 'sz',
    };

    // 加入自选
    const watchlist = app.globalData.watchlist;
    if (!watchlist.find(s => s.code === stock.code)) {
      watchlist.unshift(stock);
      app.globalData.watchlist = watchlist;
      app.saveWatchlist();
    }

    app.switchStock(stock);
    this.canvasCtx = null;
    this.setData({
      stockCode: stock.code,
      stockName: stock.name,
      showSearch: false,
      searchKeyword: '',
      searchResults: [],
    });
    // Canvas被wx:if重新创建，需重新初始化 + 加载数据
    this.loadData();
    wx.nextTick(() => {
      this.initCanvas();
    });
  },

  // 图表触摸事件
  onChartTouch(e) {
    const touches = e.touches;
    if (touches.length === 0) {
      this.setData({ crosshair: null });
      return;
    }

    const { x, y } = touches[0];
    const { klines, turningPointList } = this.data;
    if (klines.length === 0) return;

    // 计算触摸位置对应的K线索引
    const chartW = this.canvasWidth - 50; // 减去右侧留白
    const candleW = chartW / Math.max(klines.length, 1);
    const visibleCount = Math.floor(chartW / Math.max(candleW, 2));
    const startIdx = Math.max(0, klines.length - visibleCount);

    const touchIndex = Math.floor(x / candleW) + startIdx;
    if (touchIndex < 0 || touchIndex >= klines.length) return;

    // 检查是否点击了拐点
    const nearPoint = turningPointList.find(p =>
      Math.abs(p.index - touchIndex) <= 1
    );

    this.setData({
      crosshair: { x, y, index: touchIndex, kline: klines[touchIndex] },
      selectedPoint: nearPoint || null,
      showPointDetail: !!nearPoint,
    });
  },

  onChartTouchEnd() {
    this.setData({ crosshair: null });
  },

  // 阻止事件冒泡（搜索面板用）
  noop() {},

  // 关闭拐点详情
  onClosePointDetail() {
    this.setData({ showPointDetail: false, selectedPoint: null });
  },

  // 查看AI详细分析
  onViewAnalysis() {
    if (!this.data.selectedPoint) return;
    const point = this.data.selectedPoint;
    const context = turningPoints.getAnalysisContext(
      this.data.turningPointList,
      this.data.turningPointList.indexOf(point),
      this.data.klines
    );

    // 存储分析上下文到全局
    app.globalData.currentAnalysis = {
      point,
      context,
      stockName: this.data.stockName,
      stockCode: this.data.stockCode,
      klines: this.data.klines,
    };

    wx.switchTab({
      url: '/pages/analysis/analysis'
    });
  },

  // ============ Canvas 绘制 ============
  drawChart() {
    const ctx = this.canvasCtx;
    if (!ctx) { console.warn('[drawChart] canvasCtx为空，跳过绘制'); return; }

    const W = this.canvasWidth;
    const H = this.canvasHeight;
    const { klines, turningPointList, keyLevels } = this.data;

    if (klines.length === 0) { console.warn('[drawChart] klines为空，跳过绘制'); return; }

    console.log(`[drawChart] 开始绘制: ${W}x${H}, klines=${klines.length}, points=${turningPointList.length}`);

    // 清空+填充深色背景（确保Canvas区域可见）
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, W, H);

    // 布局
    const padding = { top: 10, right: 45, bottom: 0, left: 10 };
    const chartH = H - 60;       // 主图高度
    const volumeH = 50;          // 成交量高度
    const volumeY = chartH + 5;

    const chartW = W - padding.left - padding.right;

    // 可见K线范围（最近N根）
    const maxVisible = Math.floor(chartW / 3); // 最小3px间距
    const visibleKlines = klines.slice(-maxVisible);
    const startIdx = klines.length - visibleKlines.length;

    const candleSpacing = chartW / Math.max(visibleKlines.length, 1);
    const candleW = Math.max(1, candleSpacing * 0.7);
    const gap = candleSpacing - candleW;

    // 计算价格范围
    const allHighs = visibleKlines.map(k => k.high);
    const allLows = visibleKlines.map(k => k.low);
    const priceMax = Math.max(...allHighs) * 1.002;
    const priceMin = Math.min(...allLows) * 0.998;
    const priceRange = priceMax - priceMin || 1;

    const toY = (price) => chartH - ((price - priceMin) / priceRange) * chartH;

    // 成交量范围
    const maxVol = Math.max(...visibleKlines.map(k => k.volume), 1);

    // --- 绘制网格 ---
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 0.5;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const y = (chartH / gridLines) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(W - padding.right, y);
      ctx.stroke();

      // 价格标签
      const price = priceMax - (priceRange / gridLines) * i;
      ctx.fillStyle = '#64748b';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(price.toFixed(2), W - 2, y + 3);
    }

    // --- 绘制MA均线 ---
    const drawMA = (period, color) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      let started = false;
      for (let i = period - 1; i < visibleKlines.length; i++) {
        const slice = visibleKlines.slice(i - period + 1, i + 1);
        const avg = slice.reduce((s, k) => s + k.close, 0) / period;
        const x = padding.left + i * candleSpacing + candleSpacing / 2;
        const y = toY(avg);
        if (!started) { ctx.moveTo(x, y); started = true; }
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };

    drawMA(5, '#f59e0b');   // MA5 黄色
    drawMA(10, '#ec4899');  // MA10 粉色
    drawMA(20, '#3b82f6');  // MA20 蓝色

    // --- 绘制K线 ---
    for (let i = 0; i < visibleKlines.length; i++) {
      const k = visibleKlines[i];
      const x = padding.left + i * candleSpacing + gap / 2;
      const openY = toY(k.open);
      const closeY = toY(k.close);
      const highY = toY(k.high);
      const lowY = toY(k.low);

      const isUp = k.close >= k.open;
      const color = isUp ? '#ef4444' : '#22c55e';
      const fillColor = isUp ? '#ef4444' : '#1a3a2a';

      // 影线
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x + candleW / 2, highY);
      ctx.lineTo(x + candleW / 2, lowY);
      ctx.stroke();

      // 实体
      const bodyTop = Math.min(openY, closeY);
      const bodyH = Math.max(1, Math.abs(closeY - openY));
      ctx.fillStyle = fillColor;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.fillRect(x, bodyTop, candleW, bodyH);
      ctx.strokeRect(x, bodyTop, candleW, bodyH);
    }

    // --- 绘制拐点标记 ---
    turningPointList.forEach(point => {
      const relIdx = point.index - startIdx;
      if (relIdx < 0 || relIdx >= visibleKlines.length) return;

      const x = padding.left + relIdx * candleSpacing + candleSpacing / 2;
      const y = point.type === 'peak' ? toY(point.price) - 12 : toY(point.price) + 12;

      // 箭头标记
      ctx.fillStyle = point.type === 'peak' ? '#ef4444' : '#22c55e';
      ctx.beginPath();
      if (point.type === 'peak') {
        // 向下三角
        ctx.moveTo(x, y);
        ctx.lineTo(x - 6, y - 10);
        ctx.lineTo(x + 6, y - 10);
        ctx.closePath();
      } else {
        // 向上三角
        ctx.moveTo(x, y);
        ctx.lineTo(x - 6, y + 10);
        ctx.lineTo(x + 6, y + 10);
        ctx.closePath();
      }
      ctx.fill();

      // 强度和序号
      ctx.fillStyle = '#f8fafc';
      ctx.font = 'bold 9px sans-serif';
      ctx.textAlign = 'center';
      const labelY = point.type === 'peak' ? y - 14 : y + 20;
      ctx.fillText(`${point.strength}`, x, labelY);
    });

    // --- 绘制关键支撑/压力线 ---
    const drawLevelLine = (price, color, dash = false) => {
      const y = toY(price);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      if (dash) ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(W - padding.right, y);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = color;
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(price.toFixed(2), padding.left + 2, y - 2);
    };

    if (keyLevels.nearestResistance) {
      drawLevelLine(keyLevels.nearestResistance, '#ef4444aa', true);
    }
    if (keyLevels.nearestSupport) {
      drawLevelLine(keyLevels.nearestSupport, '#22c55eaa', true);
    }

    // --- 绘制成交量 ---
    for (let i = 0; i < visibleKlines.length; i++) {
      const k = visibleKlines[i];
      const x = padding.left + i * candleSpacing + gap / 2;
      const volH = (k.volume / maxVol) * volumeH;
      const isUp = k.close >= k.open;
      ctx.fillStyle = isUp ? 'rgba(239,68,68,0.4)' : 'rgba(34,197,94,0.4)';
      ctx.fillRect(x, volumeY + volumeH - volH, candleW, Math.max(1, volH));
    }

    // 成交量分割线
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding.left, volumeY);
    ctx.lineTo(W - padding.right, volumeY);
    ctx.stroke();

    // --- 绘制十字线 ---
    if (this.data.crosshair) {
      const { x, y } = this.data.crosshair;
      ctx.strokeStyle = 'rgba(255,255,255,0.5)';
      ctx.lineWidth = 0.5;
      ctx.setLineDash([2, 4]);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, chartH);
      ctx.moveTo(padding.left, y);
      ctx.lineTo(W - padding.right, y);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // --- MA图例 ---
    const legendY = padding.top + 15;
    ctx.font = '10px sans-serif';
    const legends = [
      { label: 'MA5', color: '#f59e0b' },
      { label: 'MA10', color: '#ec4899' },
      { label: 'MA20', color: '#3b82f6' },
    ];
    let legendX = padding.left;
    legends.forEach(l => {
      ctx.fillStyle = l.color;
      const textW = ctx.measureText(l.label).width + 20;
      ctx.fillText(l.label, legendX, legendY);
      legendX += textW;
    });
  },
});
