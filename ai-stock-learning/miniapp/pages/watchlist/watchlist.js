// 自选页
const app = getApp();
const marketData = require('../../services/market-data');

Page({
  data: {
    watchlist: [],
    quotes: {},       // 实时行情缓存
    loadingQuotes: false,
    editing: false,
  },

  onShow() {
    this.loadWatchlist();
    this.fetchQuotes();
  },

  loadWatchlist() {
    const list = app.globalData.watchlist || [];
    this.setData({ watchlist: list });
  },

  async fetchQuotes() {
    const { watchlist } = this.data;
    if (watchlist.length === 0) return;

    this.setData({ loadingQuotes: true });
    const quotes = {};

    // 并发获取所有自选股行情
    const promises = watchlist.map(stock =>
      marketData.fetchQuote(stock.code)
        .then(quote => { quotes[stock.code] = quote; })
        .catch(() => { quotes[stock.code] = null; })
    );

    await Promise.allSettled(promises);
    this.setData({ quotes, loadingQuotes: false });
  },

  // 点击股票 → 切换行情页
  onSelectStock(e) {
    const { code, name } = e.currentTarget.dataset;
    if (!code) return;
    const stock = { code, name: name || code, market: code.startsWith('6') ? 'sh' : 'sz' };
    app.switchStock(stock);
    wx.switchTab({ url: '/pages/chart/chart' });
  },

  // 删除自选
  onDeleteStock(e) {
    const { code } = e.currentTarget.dataset;
    wx.showModal({
      title: '删除自选',
      content: '确认从自选列表中移除？',
      success: (res) => {
        if (res.confirm) {
          app.globalData.watchlist = app.globalData.watchlist.filter(s => s.code !== code);
          app.saveWatchlist();
          this.loadWatchlist();
          this.fetchQuotes();
        }
      }
    });
  },

  // 编辑模式
  onToggleEdit() {
    this.setData({ editing: !this.data.editing });
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.fetchQuotes().then(() => wx.stopPullDownRefresh());
  },

  // 分享
  onShareAppMessage() {
    return {
      title: 'AI K线拐点分析 - 智能识别买卖信号',
      path: '/pages/chart/chart'
    };
  },
});
