// ──────────────────────────────────────
// 今天吃什么 — 美食抽奖小程序
// 抽奖 + 收藏柜 主逻辑
// ──────────────────────────────────────

const app = getApp();

// ── 菜品库 ──
const MENU = [
  { id: 'pizza', name: '🍕 意式披萨', img: 'https://cdn-icons-png.flaticon.com/512/1046/1046784.png' },
  { id: 'sushi', name: '🍣 三文鱼寿司', img: 'https://cdn-icons-png.flaticon.com/512/2948/2948759.png' },
  { id: 'ramen', name: '🍜 豚骨拉面', img: 'https://cdn-icons-png.flaticon.com/512/2933/2933244.png' },
  { id: 'burger', name: '🍔 芝士汉堡', img: 'https://cdn-icons-png.flaticon.com/512/1046/1046780.png' },
  { id: 'taco', name: '🌮 香脆塔可', img: 'https://cdn-icons-png.flaticon.com/512/3361/3361676.png' },
  { id: 'donut', name: '🍩 甜甜圈', img: 'https://cdn-icons-png.flaticon.com/512/1046/1046774.png' },
  { id: 'curry', name: '🍛 日式咖喱', img: 'https://cdn-icons-png.flaticon.com/512/2948/2948717.png' },
  { id: 'salad', name: '🥗 农场沙拉', img: 'https://cdn-icons-png.flaticon.com/512/2948/2948778.png' },
  { id: 'bento', name: '🍱 照烧便当', img: 'https://cdn-icons-png.flaticon.com/512/883/883731.png' },
  { id: 'dumpling', name: '🥟 水晶虾饺', img: 'https://cdn-icons-png.flaticon.com/512/3026/3026771.png' },
  { id: 'cake', name: '🍰 草莓蛋糕', img: 'https://cdn-icons-png.flaticon.com/512/3069/3069588.png' },
  { id: 'kimbap', name: '🍙 紫菜包饭', img: 'https://cdn-icons-png.flaticon.com/512/7724/7724488.png' },
];

const STORAGE_COLLECT = 'yummy_collected_ids';
const STORAGE_LAST_DATE = 'yummy_last_lottery_date';

// ── 工具函数 ──
function getTodayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
}

Page({
  data: {
    theme: 'light',
    viewMode: 'lottery',
    currentDish: MENU[0],
    rewardMsg: '⭐ 每天首次抽奖必得新菜品！解锁后放入柜子 ⭐',
    collectedDishes: [],
  },

  // ── 内部状态 ──
  _collectedIds: [],
  _todayHasDrawn: false,

  // ════════════════════════════════
  // 生命周期
  // ════════════════════════════════

  onLoad() {
    // 初始化主题
    const theme = app ? app.getCurrentTheme() : 'light';
    this.setData({ theme });
    this.syncPageColors(theme);

    // 加载数据
    this.loadCollection();
    this.checkDailyStatus();
    this.initDefaultDisplay();
    this.renderCabinet();
  },

  onShow() {
    // 同步主题
    if (app) {
      const theme = app.getCurrentTheme();
      if (theme !== this.data.theme) {
        this.setData({ theme });
        this.syncPageColors(theme);
      }
    }
    // 日切后刷新
    this.checkDailyStatus();
  },

  // ════════════════════════════════
  // 主题
  // ════════════════════════════════

  syncPageColors(theme) {
    const isLight = theme === 'light';
    wx.setNavigationBarColor({
      frontColor: '#ffffff',
      backgroundColor: isLight ? '#ffaa5e' : '#6b3a1e',
    });
    wx.setBackgroundColor({
      backgroundColor: isLight ? '#fff2df' : '#1a1410',
    });
  },

  // ════════════════════════════════
  // 数据持久化
  // ════════════════════════════════

  loadCollection() {
    try {
      const stored = wx.getStorageSync(STORAGE_COLLECT);
      if (stored) {
        this._collectedIds = JSON.parse(stored);
        if (!Array.isArray(this._collectedIds)) this._collectedIds = [];
      }
    } catch (e) {
      this._collectedIds = [];
    }

    // 新手体验：无收藏时赠送一个基础菜品
    if (this._collectedIds.length === 0) {
      this._collectedIds = [MENU[0].id];
      this.saveCollection();
    }

    // 去重
    this._collectedIds = [...new Set(this._collectedIds)];
    this.saveCollection();
  },

  saveCollection() {
    wx.setStorageSync(STORAGE_COLLECT, JSON.stringify(this._collectedIds));
  },

  checkDailyStatus() {
    const lastDate = wx.getStorageSync(STORAGE_LAST_DATE);
    const today = getTodayStr();
    this._todayHasDrawn = (lastDate === today);

    if (this._todayHasDrawn) {
      this.setData({ rewardMsg: '🍬 今日已抽过奖啦！明天再来拿新菜品吧 🍬' });
    } else {
      this.setData({ rewardMsg: '⭐ 每天首次抽奖必得新菜品！解锁后放入柜子 ⭐' });
    }
  },

  markTodayDrawn() {
    wx.setStorageSync(STORAGE_LAST_DATE, getTodayStr());
    this._todayHasDrawn = true;
    this.setData({ rewardMsg: '✅ 今日福利已领！明日继续收集新料理 ✅' });
  },

  // ════════════════════════════════
  // 渲染收藏柜
  // ════════════════════════════════

  renderCabinet() {
    const collectedDishes = this._collectedIds
      .map(id => MENU.find(d => d.id === id))
      .filter(d => d);
    this.setData({ collectedDishes });
  },

  // ════════════════════════════════
  // 默认展示
  // ════════════════════════════════

  initDefaultDisplay() {
    if (this._collectedIds.length > 0) {
      const firstOwned = MENU.find(d => d.id === this._collectedIds[0]);
      if (firstOwned) this.setData({ currentDish: firstOwned });
    }
  },

  // ════════════════════════════════
  // 抽奖核心逻辑
  // ════════════════════════════════

  performLottery() {
    const allIds = MENU.map(d => d.id);
    const isFullCollection = this._collectedIds.length === allIds.length;
    let selectedDish = null;
    let msgExtra = '';

    // 每日首次抽奖 且 图鉴未满 → 必得未收集菜品
    if (!this._todayHasDrawn && !isFullCollection) {
      const uncollected = allIds.filter(id => !this._collectedIds.includes(id));
      if (uncollected.length > 0) {
        const newId = uncollected[Math.floor(Math.random() * uncollected.length)];
        selectedDish = MENU.find(d => d.id === newId);
        this.addToCollection(selectedDish.id);
        msgExtra = ' 🎉 新料理上柜！🎉';
        this.markTodayDrawn();
      }
    } else {
      // 普通抽奖
      selectedDish = MENU[Math.floor(Math.random() * MENU.length)];
      const wasNew = this.addToCollection(selectedDish.id);
      if (wasNew) {
        msgExtra = ' 🌟 意外收获！新菜品进柜 🌟';
      } else {
        msgExtra = ' 🍽️ 回味经典，再次品尝 🍽️';
      }

      if (!this._todayHasDrawn && isFullCollection) {
        this.markTodayDrawn();
        msgExtra = ' 🏆 美食大师！全图鉴已解锁 🏆';
      }
      if (this._todayHasDrawn && !wasNew) {
        msgExtra = ' 🍴 今日复抽，美味依旧 🍴';
      }
    }

    // 兜底
    if (!selectedDish) {
      selectedDish = MENU[0];
    }

    // 更新视图
    this.setData({ currentDish: selectedDish });

    // 更新提示文案
    let rewardMsg;
    if (this._collectedIds.length === allIds.length) {
      rewardMsg = '🏅 恭喜集齐全套美食！每日都可以快乐抽奖 🏅';
    } else if (msgExtra.includes('新料理') || msgExtra.includes('新菜品')) {
      rewardMsg = `✨ 获得 ${selectedDish.name} ✨${msgExtra}`;
    } else {
      rewardMsg = msgExtra;
    }
    this.setData({ rewardMsg });

    // 刷新柜子
    this.renderCabinet();
  },

  /**
   * 添加菜品到收藏，返回是否新收藏
   */
  addToCollection(dishId) {
    if (!this._collectedIds.includes(dishId)) {
      this._collectedIds.push(dishId);
      this.saveCollection();
      return true;
    }
    return false;
  },

  // ════════════════════════════════
  // 视图切换
  // ════════════════════════════════

  switchToLottery() {
    this.setData({ viewMode: 'lottery' });
  },

  switchToCollection() {
    this.renderCabinet();
    this.setData({ viewMode: 'collection' });
  },
});
