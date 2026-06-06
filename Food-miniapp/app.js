// ──────────────────────────────────────
// 今天吃什么 · 美食抽奖小程序
// 支持黑夜/白天双模式切换
// ──────────────────────────────────────

App({
  globalData: {
    themeMode: 'auto',
    currentTheme: 'light',
  },

  onLaunch() {
    const saved = wx.getStorageSync('themeMode');
    if (saved) {
      this.globalData.themeMode = saved;
    }
    this.applyTheme();
  },

  setThemeMode(mode) {
    this.globalData.themeMode = mode;
    wx.setStorageSync('themeMode', mode);
    this.applyTheme();
  },

  applyTheme() {
    let theme;
    if (this.globalData.themeMode === 'auto') {
      const sysInfo = wx.getSystemInfoSync();
      theme = sysInfo.theme || 'light';
    } else {
      theme = this.globalData.themeMode;
    }
    this.globalData.currentTheme = theme;
  },

  getCurrentTheme() {
    return this.globalData.currentTheme;
  },
});
