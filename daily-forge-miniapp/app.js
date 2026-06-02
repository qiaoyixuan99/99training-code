// ──────────────────────────────────────
// Daily Forge — 微信小程序版
// 支持黑夜/白天双模式切换
// ──────────────────────────────────────

App({
  globalData: {
    // 主题模式: 'auto' | 'light' | 'dark'
    themeMode: 'auto',
    // 当前生效的主题: 'light' | 'dark'
    currentTheme: 'dark',
  },

  onLaunch() {
    // 读取用户保存的主题偏好
    const saved = wx.getStorageSync('themeMode');
    if (saved) {
      this.globalData.themeMode = saved;
    }
    this.applyTheme();
  },

  /**
   * 设置主题模式
   * @param {'auto' | 'light' | 'dark'} mode
   */
  setThemeMode(mode) {
    this.globalData.themeMode = mode;
    wx.setStorageSync('themeMode', mode);
    this.applyTheme();
  },

  /**
   * 根据当前模式应用主题
   */
  applyTheme() {
    let theme;
    if (this.globalData.themeMode === 'auto') {
      // 跟随系统
      const sysInfo = wx.getSystemInfoSync();
      theme = sysInfo.theme || 'dark';
    } else {
      theme = this.globalData.themeMode;
    }
    this.globalData.currentTheme = theme;
  },

  /**
   * 获取当前主题
   * @returns {'light' | 'dark'}
   */
  getCurrentTheme() {
    return this.globalData.currentTheme;
  },
});
