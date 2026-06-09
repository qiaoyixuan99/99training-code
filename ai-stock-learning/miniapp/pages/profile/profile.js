// 个人中心页
const app = getApp();

Page({
  data: {
    analysisCount: 0,
    watchCount: 0,
    analysisHistory: [],
    showHistory: false,
  },

  onShow() {
    const history = app.globalData.analysisHistory || [];
    const watchlist = app.globalData.watchlist || [];

    this.setData({
      analysisCount: history.length,
      watchCount: watchlist.length,
      analysisHistory: history.slice(0, 10),
    });
  },

  onToggleHistory() {
    this.setData({ showHistory: !this.data.showHistory });
  },

  onClearHistory() {
    wx.showModal({
      title: '清空历史',
      content: '确认清空所有分析记录？',
      success: (res) => {
        if (res.confirm) {
          app.globalData.analysisHistory = [];
          app.saveAnalysisHistory();
          this.setData({
            analysisCount: 0,
            analysisHistory: [],
            showHistory: false,
          });
          wx.showToast({ title: '已清空', icon: 'success' });
        }
      }
    });
  },

  // 分享
  onShareAppMessage() {
    return {
      title: 'AI K线拐点分析 - 智能识别买卖信号',
      path: '/pages/chart/chart'
    };
  },
});
