const app = getApp();
const util = require('../../utils/util.js');

Page({
  data: {
    cartItems: [],
    totalPrice: 0,
    totalCalories: 0,
    allChecked: true,
    loveAnimations: [],
  },

  onShow() {
    this.refreshCart();
  },

  refreshCart() {
    const cart = app.globalData.cart || [];
    const cartItems = cart.map((item) => {
      const itemTotal =
        (item.isDouble
          ? item.price * 2 * 0.88
          : item.price) * item.quantity;
      const calTotal =
        (item.isDouble ? item.calories * 2 : item.calories) * item.quantity;
      return {
        ...item,
        checked: true,
        itemTotal: Math.round(itemTotal * 100) / 100,
        calTotal,
        displayPrice: item.isDouble
          ? '¥' + (item.price * 2 * 0.88).toFixed(2)
          : '¥' + item.price.toFixed(2),
      };
    });

    const totalPrice = cartItems.reduce(
      (sum, item) => sum + item.itemTotal,
      0
    );
    const totalCalories = cartItems.reduce(
      (sum, item) => sum + item.calTotal,
      0
    );

    this.setData({
      cartItems,
      totalPrice: Math.round(totalPrice * 100) / 100,
      totalCalories,
    });
  },

  // 数量增加
  onIncrease(e) {
    const { index } = e.currentTarget.dataset;
    const item = this.data.cartItems[index];
    app.updateCartItem(item.foodId, item.isDouble, item.quantity + 1);
    this.refreshCart();
  },

  // 数量减少
  onDecrease(e) {
    const { index } = e.currentTarget.dataset;
    const item = this.data.cartItems[index];
    if (item.quantity <= 1) {
      this.onRemove(e);
      return;
    }
    app.updateCartItem(item.foodId, item.isDouble, item.quantity - 1);
    this.refreshCart();
  },

  // 删除项
  onRemove(e) {
    const { index } = e.currentTarget.dataset;
    const item = this.data.cartItems[index];
    util.showConfirm(`确认移除「${item.name}」吗？`).then((confirm) => {
      if (confirm) {
        app.updateCartItem(item.foodId, item.isDouble, 0);
        this.refreshCart();
        util.showToast('已移除');
      }
    });
  },

  // 切换情侣份
  onToggleDouble(e) {
    const { index } = e.currentTarget.dataset;
    const item = this.data.cartItems[index];
    // 先移除旧的，再添加新的
    app.updateCartItem(item.foodId, false, 0);
    app.addToCart({
      foodId: item.foodId,
      name: item.name,
      image: item.image,
      price: item.price,
      calories: item.calories,
      category: item.category,
      isDouble: !item.isDouble,
      quantity: item.quantity,
    });
    this.refreshCart();
    util.showLoveAnimation(this);
  },

  // 清空购物车
  onClearCart() {
    if (this.data.cartItems.length === 0) return;
    util.showConfirm('确认清空购物车吗？所有美食都会被移除哦～').then(
      (confirm) => {
        if (confirm) {
          app.clearCart();
          this.refreshCart();
          util.showToast('购物车已清空 🧹');
        }
      }
    );
  },

  // 去结算
  onCheckout() {
    if (this.data.cartItems.length === 0) {
      util.showToast('购物车空空如也～先去逛逛吧 🛒');
      return;
    }
    wx.navigateTo({ url: '/pages/order/order' });
  },

  onShareAppMessage() {
    return {
      title: `情侣美食记 - 我的购物车 💕`,
      path: '/pages/cart/cart',
    };
  },
});
