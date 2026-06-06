const app = getApp();
const util = require('../../utils/util.js');

Page({
  data: {
    orderItems: [],
    totalPrice: 0,
    totalCalories: 0,
    note: '',
    loveAnimations: [],
    submitting: false,
  },

  onLoad(options) {
    if (options.item) {
      // 单个立即购买
      try {
        const item = JSON.parse(decodeURIComponent(options.item));
        const itemTotal =
          (item.isDouble ? item.price * 2 * 0.88 : item.price) *
          item.quantity;
        this.setData({
          orderItems: [
            {
              ...item,
              itemTotal: Math.round(itemTotal * 100) / 100,
            },
          ],
          totalPrice: Math.round(itemTotal * 100) / 100,
          totalCalories:
            (item.isDouble ? item.calories * 2 : item.calories) *
            item.quantity,
        });
      } catch (e) {
        console.error('解析订单项失败:', e);
      }
    } else {
      // 购物车结算
      this.loadFromCart();
    }
  },

  loadFromCart() {
    const cart = app.globalData.cart || [];
    const orderItems = cart.map((item) => {
      const itemTotal =
        (item.isDouble ? item.price * 2 * 0.88 : item.price) *
        item.quantity;
      return {
        ...item,
        itemTotal: Math.round(itemTotal * 100) / 100,
        calTotal:
          (item.isDouble ? item.calories * 2 : item.calories) * item.quantity,
      };
    });

    const totalPrice = orderItems.reduce(
      (sum, item) => sum + item.itemTotal,
      0
    );
    const totalCalories = orderItems.reduce(
      (sum, item) => sum + item.calTotal,
      0
    );

    this.setData({
      orderItems,
      totalPrice: Math.round(totalPrice * 100) / 100,
      totalCalories,
    });
  },

  // 备注输入
  onNoteInput(e) {
    this.setData({ note: e.detail.value });
  },

  // 提交订单
  async onSubmitOrder() {
    if (this.data.submitting) return;
    this.setData({ submitting: true });

    try {
      // 调用云函数下单
      const res = await wx.cloud.callFunction({
        name: 'placeOrder',
        data: {
          items: this.data.orderItems,
          totalPrice: this.data.totalPrice,
          totalCalories: this.data.totalCalories,
          note: this.data.note,
          date: util.getToday(),
        },
      });

      // 清空购物车
      app.clearCart();

      // 触发甜蜜动画
      util.showLoveAnimation(this);

      wx.showModal({
        title: '下单成功 🎉',
        content: `美食正在准备中！\n已自动同步到「饮食日记」\n总卡路里：${this.data.totalCalories} kcal\n\n祝你和TA用餐愉快 💕`,
        confirmText: '去看看日记',
        cancelText: '继续逛逛',
        confirmColor: '#FF7EB3',
        success: (modalRes) => {
          if (modalRes.confirm) {
            wx.switchTab({ url: '/pages/diary/diary' });
          } else {
            wx.switchTab({ url: '/pages/index/index' });
          }
        },
      });
    } catch (err) {
      console.error('下单失败:', err);
      // 离线模式：本地保存订单到日记
      this.saveOrderLocally();

      wx.showModal({
        title: '下单成功 🎉',
        content: '订单已记录（离线模式），已同步到饮食日记 💕',
        confirmText: '去看看日记',
        cancelText: '继续逛逛',
        confirmColor: '#FF7EB3',
        success: (modalRes) => {
          app.clearCart();
          if (modalRes.confirm) {
            wx.switchTab({ url: '/pages/diary/diary' });
          } else {
            wx.switchTab({ url: '/pages/index/index' });
          }
        },
      });
    }
    this.setData({ submitting: false });
  },

  // 本地保存订单
  saveOrderLocally() {
    const today = util.getToday();
    const diary = wx.getStorageSync('diary') || {};
    if (!diary[today]) {
      diary[today] = {
        date: today,
        meals: {
          breakfast: { items: [], totalCal: 0 },
          lunch: { items: [], totalCal: 0 },
          dinner: { items: [], totalCal: 0 },
          snack: { items: [], totalCal: 0 },
        },
      };
    }

    // 判定当前应该归到哪一餐
    const hour = new Date().getHours();
    let mealType = 'snack';
    if (hour >= 6 && hour < 10) mealType = 'breakfast';
    else if (hour >= 10 && hour < 14) mealType = 'lunch';
    else if (hour >= 14 && hour < 17) mealType = 'snack';
    else if (hour >= 17 && hour < 21) mealType = 'dinner';

    const meal = diary[today].meals[mealType];
    this.data.orderItems.forEach((item) => {
      meal.items.push({
        foodId: item.foodId,
        name: item.name,
        image: item.image,
        price: item.price,
        calories: item.calories,
        isDouble: item.isDouble,
        quantity: item.quantity,
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      });
      meal.totalCal += (item.isDouble ? item.calories * 2 : item.calories) * item.quantity;
    });

    wx.setStorageSync('diary', diary);
  },

  onShareAppMessage() {
    return {
      title: `刚下单了一桌美食 💕`,
      path: '/pages/index/index',
    };
  },
});
