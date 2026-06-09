// AI K线拐点分析器
App({
  globalData: {
    // 当前查看的股票
    currentStock: {
      code: '000001',
      market: 'sz',      // sh/sz
      name: '平安银行',
      price: 0,
      change: 0,
      changePercent: 0
    },
    // 当前K线周期
    currentPeriod: 'day',  // day/week/month/60min/30min/15min/5min
    // 自选股列表
    watchlist: [],
    // AI分析历史
    analysisHistory: [],
    // 系统信息
    statusBarHeight: 0,
    navBarHeight: 0
  },

  onLaunch() {
    // 恢复自选股（过滤掉无效数据）
    const watchlist = wx.getStorageSync('watchlist');
    if (watchlist && watchlist.length > 0) {
      const validList = watchlist.filter(item => item && item.code);
      this.globalData.watchlist = validList;
      if (validList.length > 0) {
        this.globalData.currentStock = validList[0];
      }
    }
    // 恢复分析历史
    const history = wx.getStorageSync('analysisHistory');
    if (history && history.length > 0) {
      this.globalData.analysisHistory = history.filter(item => item && item.stockCode);
    }
    // 系统信息
    const sysInfo = wx.getSystemInfoSync();
    this.globalData.statusBarHeight = sysInfo.statusBarHeight;
    this.globalData.navBarHeight = sysInfo.statusBarHeight + 44;
  },

  // 切换股票
  switchStock(stock) {
    this.globalData.currentStock = stock;
  },

  // 保存自选股
  saveWatchlist() {
    wx.setStorageSync('watchlist', this.globalData.watchlist);
  },

  // 保存分析历史
  saveAnalysisHistory() {
    wx.setStorageSync('analysisHistory', this.globalData.analysisHistory.slice(0, 50));
  }
});
