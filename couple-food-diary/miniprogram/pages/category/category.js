const app = getApp();
const util = require('../../utils/util.js');

Page({
  data: {
    categoryId: '',
    categoryName: '',
    foods: [],
    loveAnimations: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    sortType: 'default', // default, price-asc, price-desc, cal-asc, cal-desc
  },

  onLoad(options) {
    const { id, name } = options;
    this.setData({ categoryId: id, categoryName: name });
    wx.setNavigationBarTitle({ title: name || '分类美食' });
    this.loadFoods();
  },

  onPullDownRefresh() {
    this.setData({ page: 1, hasMore: true, foods: [] });
    this.loadFoods().then(() => wx.stopPullDownRefresh());
  },

  onReachBottom() {
    if (!this.data.hasMore || this.data.loading) return;
    this.loadMoreFoods();
  },

  async loadFoods() {
    this.setData({ loading: true });
    try {
      const db = wx.cloud.database();
      const res = await db
        .collection('foods')
        .where({ category: this.data.categoryId })
        .orderBy('createdAt', 'desc')
        .limit(this.data.pageSize)
        .get();

      this.setData({
        foods: this.sortFoods(res.data, this.data.sortType),
        hasMore: res.data.length >= this.data.pageSize,
        loading: false,
      });
    } catch (err) {
      console.error('加载分类食品失败:', err);
      // 使用本地数据
      const seedData = require('../../../seed/seedData.js');
      const foods = (seedData.default || seedData).filter(
        (f) => f.category === this.data.categoryId
      );
      this.setData({ foods, loading: false, hasMore: false });
    }
  },

  async loadMoreFoods() {
    this.setData({ loading: true });
    const { page, pageSize } = this.data;

    try {
      const db = wx.cloud.database();
      const res = await db
        .collection('foods')
        .where({ category: this.data.categoryId })
        .orderBy('createdAt', 'desc')
        .skip(page * pageSize)
        .limit(pageSize)
        .get();

      const newFoods = this.sortFoods(res.data, this.data.sortType);
      this.setData({
        foods: [...this.data.foods, ...newFoods],
        page: page + 1,
        hasMore: newFoods.length >= pageSize,
        loading: false,
      });
    } catch (err) {
      this.setData({ hasMore: false, loading: false });
    }
  },

  // 排序切换
  onSortChange(e) {
    const { type } = e.currentTarget.dataset;
    const sortType = type === this.data.sortType ? 'default' : type;
    this.setData({
      sortType,
      foods: this.sortFoods(this.data.foods, sortType),
    });
  },

  sortFoods(foods, sortType) {
    const arr = [...foods];
    switch (sortType) {
      case 'price-asc':
        return arr.sort((a, b) => a.price - b.price);
      case 'price-desc':
        return arr.sort((a, b) => b.price - a.price);
      case 'cal-asc':
        return arr.sort((a, b) => a.calories - b.calories);
      case 'cal-desc':
        return arr.sort((a, b) => b.calories - a.calories);
      default:
        return arr;
    }
  },

  onFoodTap(e) {
    const { food } = e.detail;
    wx.navigateTo({
      url: `/pages/detail/detail?id=${food._id || food.id}`,
    });
  },

  onAddCart(e) {
    const { food } = e.detail;
    app.addToCart({
      foodId: food._id || food.id,
      name: food.name,
      image: food.image,
      price: food.price,
      calories: food.calories,
      category: food.category,
      isDouble: false,
      quantity: 1,
    });
    util.showLoveAnimation(this);
    util.showToast('已加入购物车 ❤️');
  },

  onShareAppMessage() {
    return {
      title: `来看看${this.data.categoryName}美食 💕`,
      path: `/pages/category/category?id=${this.data.categoryId}&name=${this.data.categoryName}`,
    };
  },
});
