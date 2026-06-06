const app = getApp();

Component({
  properties: {
    count: {
      type: Number,
      value: 0,
    },
  },

  lifetimes: {
    attached() {
      this.updateCount();
    },
  },

  pageLifetimes: {
    show() {
      this.updateCount();
    },
  },

  methods: {
    updateCount() {
      const cart = app.globalData.cart || [];
      const total = cart.reduce((sum, item) => sum + item.quantity, 0);
      this.setData({ count: total });
    },

    onTap() {
      wx.switchTab({ url: '/pages/cart/cart' });
    },
  },
});
