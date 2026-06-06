App({
  onLaunch: function () {
    if (!wx.cloud) {
      console.error('请使用 2.2.3 或以上的基础库以使用云能力');
    } else {
      wx.cloud.init({
        env: 'couple-food-diary-0gxxxx',
        traceUser: true,
      });
    }

    // 初始化全局购物车
    const cart = wx.getStorageSync('cart') || [];
    this.globalData.cart = cart;

    // 获取系统信息
    const systemInfo = wx.getSystemInfoSync();
    this.globalData.systemInfo = systemInfo;
    this.globalData.statusBarHeight = systemInfo.statusBarHeight;
    this.globalData.navBarHeight = systemInfo.platform === 'android' ? 48 : 44;
  },

  // 添加购物车项
  addToCart: function (item) {
    const cart = this.globalData.cart;
    const idx = cart.findIndex(
      (c) => c.foodId === item.foodId && c.isDouble === item.isDouble
    );
    if (idx > -1) {
      cart[idx].quantity += item.quantity || 1;
    } else {
      cart.push({
        foodId: item.foodId,
        name: item.name,
        image: item.image,
        price: item.price,
        calories: item.calories,
        isDouble: item.isDouble || false,
        quantity: item.quantity || 1,
        category: item.category || '',
      });
    }
    this.globalData.cart = cart;
    wx.setStorageSync('cart', cart);
    this.updateCartBadge();
  },

  // 更新购物车数量
  updateCartItem: function (foodId, isDouble, quantity) {
    const cart = this.globalData.cart;
    const idx = cart.findIndex(
      (c) => c.foodId === foodId && c.isDouble === isDouble
    );
    if (idx > -1) {
      if (quantity <= 0) {
        cart.splice(idx, 1);
      } else {
        cart[idx].quantity = quantity;
      }
    }
    this.globalData.cart = cart;
    wx.setStorageSync('cart', cart);
    this.updateCartBadge();
  },

  // 清空购物车
  clearCart: function () {
    this.globalData.cart = [];
    wx.setStorageSync('cart', []);
    this.updateCartBadge();
  },

  // 更新购物车角标
  updateCartBadge: function () {
    const total = this.globalData.cart.reduce(
      (sum, item) => sum + item.quantity,
      0
    );
    if (total > 0) {
      wx.setTabBarBadge({ index: 1, text: String(total) });
    } else {
      wx.removeTabBarBadge({ index: 1 });
    }
  },

  // 获取购物车总价
  getCartTotal: function () {
    return this.globalData.cart.reduce((sum, item) => {
      const price = item.isDouble ? item.price * 2 * 0.88 : item.price;
      return sum + price * item.quantity;
    }, 0);
  },

  // 获取购物车总卡路里
  getCartCalories: function () {
    return this.globalData.cart.reduce((sum, item) => {
      const cal = item.isDouble ? item.calories * 2 : item.calories;
      return sum + cal * item.quantity;
    }, 0);
  },

  globalData: {
    cart: [],
    systemInfo: null,
    statusBarHeight: 0,
    navBarHeight: 44,
    // 7大分类
    categories: [
      { id: 'staple', name: '主食', icon: '🍚', color: '#FF7EB3' },
      { id: 'snack', name: '零食', icon: '🍿', color: '#FF9EC5' },
      { id: 'fruit', name: '水果', icon: '🍓', color: '#FF85A2' },
      { id: 'drink', name: '饮料', icon: '🥤', color: '#FFB3CC' },
      { id: 'milktea', name: '奶茶', icon: '🧋', color: '#FF7EB3' },
      { id: 'salad', name: '沙拉', icon: '🥗', color: '#FF9EC5' },
      { id: 'soup', name: '汤品', icon: '🍲', color: '#FF85A2' },
    ],
    // 甜蜜动画反馈文案
    loveMessages: [
      '❤️ 甜蜜加倍！',
      '💕 情侣份更优惠～',
      '🥰 用心为你准备！',
      '💝 爱与美食不可辜负',
      '🌸 每一口都是幸福',
      '✨ TA一定喜欢！',
      '💖 分享甜蜜时刻',
      '🎀 浪漫加分！',
    ],
  },
});
