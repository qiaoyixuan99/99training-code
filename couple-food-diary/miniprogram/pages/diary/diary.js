const app = getApp();
const util = require('../../utils/util.js');

Page({
  data: {
    selectedDate: '',
    weekDay: '',
    diaryEntry: null,
    // 7天卡路里趋势
    weekCalories: [],
    // 总计
    totalCalories: 0,
    mealTypes: [
      { key: 'breakfast', name: '🥐 早餐', icon: '🌅' },
      { key: 'lunch', name: '🍱 午餐', icon: '☀️' },
      { key: 'dinner', name: '🍲 晚餐', icon: '🌙' },
      { key: 'snack', name: '🍿 零食', icon: '🍬' },
    ],
    loveAnimations: [],
  },

  onLoad() {
    const today = util.getToday();
    this.setData({
      selectedDate: today,
      weekDay: util.getWeekday(today),
    });
    this.loadDiary(today);
    this.loadWeekCalories();
  },

  onShow() {
    this.loadDiary(this.data.selectedDate);
    this.loadWeekCalories();
  },

  // 加载指定日期的日记
  async loadDiary(date) {
    try {
      const db = wx.cloud.database();
      const res = await db
        .collection('diary')
        .where({ date })
        .limit(1)
        .get();

      if (res.data.length > 0) {
        const entry = res.data[0];
        this.setData({
          diaryEntry: entry,
          totalCalories: this.calcTotalCalories(entry),
        });
      } else {
        // 空日记模板
        this.setData({
          diaryEntry: {
            date,
            meals: {
              breakfast: { items: [], totalCal: 0 },
              lunch: { items: [], totalCal: 0 },
              dinner: { items: [], totalCal: 0 },
              snack: { items: [], totalCal: 0 },
            },
          },
          totalCalories: 0,
        });
      }
    } catch (err) {
      console.error('加载日记失败:', err);
      // 本地存储回退
      this.loadLocalDiary(date);
    }
  },

  // 本地日记加载
  loadLocalDiary(date) {
    const diary = wx.getStorageSync('diary') || {};
    const entry = diary[date] || {
      date,
      meals: {
        breakfast: { items: [], totalCal: 0 },
        lunch: { items: [], totalCal: 0 },
        dinner: { items: [], totalCal: 0 },
        snack: { items: [], totalCal: 0 },
      },
    };
    this.setData({
      diaryEntry: entry,
      totalCalories: this.calcTotalCalories(entry),
    });
  },

  // 加载7天卡路里趋势
  loadWeekCalories() {
    const diary = wx.getStorageSync('diary') || {};
    const weekCalories = [];
    let totalWeek = 0;

    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const dateStr = util.formatDate(d);
      const entry = diary[dateStr];
      const cal = entry ? this.calcTotalCalories(entry) : 0;
      totalWeek += cal;
      weekCalories.push({
        date: dateStr,
        day: util.getWeekday(dateStr),
        calories: cal,
      });
    }

    this.setData({ weekCalories, totalWeekCalories: totalWeek });
  },

  // 计算总卡路里
  calcTotalCalories(entry) {
    if (!entry || !entry.meals) return 0;
    return Object.values(entry.meals).reduce(
      (sum, meal) => sum + (meal.totalCal || 0),
      0
    );
  },

  // 日期选择
  onDateChange(e) {
    const date = e.detail.value;
    this.setData({
      selectedDate: date,
      weekDay: util.getWeekday(date),
    });
    this.loadDiary(date);
  },

  // 前一天
  onPrevDay() {
    const d = new Date(this.data.selectedDate);
    d.setDate(d.getDate() - 1);
    const date = util.formatDate(d);
    this.setData({ selectedDate: date, weekDay: util.getWeekday(date) });
    this.loadDiary(date);
  },

  // 后一天
  onNextDay() {
    const d = new Date(this.data.selectedDate);
    d.setDate(d.getDate() + 1);
    const date = util.formatDate(d);
    this.setData({ selectedDate: date, weekDay: util.getWeekday(date) });
    this.loadDiary(date);
  },

  // 删除日记项
  onDeleteItem(e) {
    const { mealtype, index } = e.currentTarget.dataset;
    const entry = this.data.diaryEntry;
    const items = entry.meals[mealtype].items;

    util.showConfirm('确定删除这条记录吗？').then((confirm) => {
      if (!confirm) return;

      const removed = items[index];
      items.splice(index, 1);
      entry.meals[mealtype].totalCal -= removed.calories * removed.quantity * (removed.isDouble ? 2 : 1);
      if (entry.meals[mealtype].totalCal < 0) entry.meals[mealtype].totalCal = 0;

      this.setData({
        diaryEntry: entry,
        totalCalories: this.calcTotalCalories(entry),
      });

      // 保存到本地存储
      const diary = wx.getStorageSync('diary') || {};
      diary[entry.date] = entry;
      wx.setStorageSync('diary', diary);

      this.loadWeekCalories();
      util.showToast('已删除');
    });
  },

  // 获取每日建议卡路里
  getDailyRecommend() {
    return 2000; // 成人每日建议摄入
  },

  // 卡路里进度百分比
  getCalPercent() {
    return Math.min(
      100,
      Math.round((this.data.totalCalories / this.getDailyRecommend()) * 100)
    );
  },

  onShareAppMessage() {
    return {
      title: `情侣美食记 - 饮食日记 💕`,
      path: '/pages/diary/diary',
    };
  },
});
