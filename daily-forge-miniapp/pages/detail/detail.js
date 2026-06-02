// ──────────────────────────────────────
// Daily Forge — 任务详情页
// 展示每个任务的完整学习内容、资源链接
// ──────────────────────────────────────

const { TASK_RESOURCES } = require('../../utils/task-resources');

const app = getApp();

Page({
  data: {
    theme: 'dark',
    task: null,
    activeTab: 0,
    showSearch: false,
    searchQuery: '',
    searchResults: [],
    searchLoading: false,
    expandedSections: [],
    linkCopied: false,
  },

  onLoad(options) {
    const taskId = options.id || 'morning';
    const taskData = TASK_RESOURCES[taskId];

    if (!taskData) {
      wx.showToast({ title: '任务不存在', icon: 'error' });
      return;
    }

    // 初始化主题
    const theme = app.getCurrentTheme ? app.getCurrentTheme() : 'dark';
    this.setData({ theme, task: taskData });
    this.syncPageColors(theme);
  },

  syncPageColors(theme) {
    const isLight = theme === 'light';
    wx.setNavigationBarColor({
      frontColor: isLight ? '#000000' : '#ffffff',
      backgroundColor: isLight ? '#f5f5f7' : '#0f1117',
    });
  },

  // ── 返回 ──
  goBack() {
    wx.navigateBack();
  },

  // ── Tab 切换 ──
  switchTab(e) {
    const idx = e.currentTarget.dataset.idx;
    this.setData({ activeTab: idx });
  },

  // ── 展开/折叠 section ──
  toggleSection(e) {
    const idx = e.currentTarget.dataset.idx;
    const expanded = [...this.data.expandedSections];
    const pos = expanded.indexOf(idx);
    if (pos > -1) {
      expanded.splice(pos, 1);
    } else {
      expanded.push(idx);
    }
    this.setData({ expandedSections: expanded });
  },

  // ── 复制链接 ──
  copyLink(e) {
    const url = e.currentTarget.dataset.url;
    wx.setClipboardData({
      data: url,
      success: () => {
        this.setData({ linkCopied: true });
        setTimeout(() => this.setData({ linkCopied: false }), 2000);
      },
    });
  },

  // ── 打开链接（web-view 或复制） ──
  openLink(e) {
    const url = e.currentTarget.dataset.url;
    const name = e.currentTarget.dataset.name;

    wx.showActionSheet({
      itemList: ['复制链接', '在浏览器中打开'],
      success(res) {
        if (res.tapIndex === 0) {
          wx.setClipboardData({ data: url });
        } else if (res.tapIndex === 1) {
          wx.setClipboardData({
            data: url,
            success() {
              wx.showToast({ title: '链接已复制，请在浏览器打开', icon: 'none' });
            },
          });
        }
      },
    });
  },

  // ── 搜索功能 ──
  toggleSearch() {
    this.setData({ showSearch: !this.data.showSearch, searchResults: [], searchQuery: '' });
  },

  onSearchInput(e) {
    this.setData({ searchQuery: e.detail.value });
  },

  doSearch() {
    const query = this.data.searchQuery.trim();
    if (!query) return;

    this.setData({ searchLoading: true, searchResults: [] });

    // 使用百度搜索API作为备选（微信小程序内可用）
    // 由于小程序域名限制，我们用本地知识库匹配 + 提供搜索链接
    const task = this.data.task;
    const results = [];

    // 本地资源匹配
    if (task && task.sections) {
      task.sections.forEach(section => {
        if (section.resources) {
          section.resources.forEach(r => {
            if (r.name.toLowerCase().includes(query.toLowerCase()) ||
                (r.type && r.type.includes(query.toLowerCase()))) {
              results.push({ ...r, source: '本地资源' });
            }
          });
        }
      });
    }

    // 生成外部搜索链接
    const searchLinks = [
      { name: `🔍 在Google搜索 "${query}"`, url: `https://www.google.com/search?q=${encodeURIComponent(query)}`, source: 'Google' },
      { name: `🔍 在百度搜索 "${query}"`, url: `https://www.baidu.com/s?wd=${encodeURIComponent(query)}`, source: '百度' },
      { name: `📺 在YouTube搜索 "${query}"`, url: `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`, source: 'YouTube' },
      { name: `💻 在GitHub搜索 "${query}"`, url: `https://github.com/search?q=${encodeURIComponent(query)}`, source: 'GitHub' },
      { name: `📖 在知乎搜索 "${query}"`, url: `https://www.zhihu.com/search?type=content&q=${encodeURIComponent(query)}`, source: '知乎' },
    ];

    setTimeout(() => {
      this.setData({
        searchResults: [...results, ...searchLinks],
        searchLoading: false,
      });
    }, 300);
  },
});
