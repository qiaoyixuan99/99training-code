const app = getApp();
const util = require('../../utils/util.js');

Page({
  data: {
    statusBarHeight: app.globalData.statusBarHeight,
    navBarHeight: app.globalData.navBarHeight,
    categories: app.globalData.categories,
    activeCategory: 'all',
    foods: [],
    allFoods: [],
    filteredFoods: [],
    searchKeyword: '',
    loveAnimations: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    cartCount: 0,
  },

  onLoad() {
    this.loadFoods();
  },

  onShow() {
    this.updateCartCount();
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.setData({ page: 1, hasMore: true, foods: [] });
    this.loadFoods().then(() => wx.stopPullDownRefresh());
  },

  // 上拉加载更多
  onReachBottom() {
    if (!this.data.hasMore || this.data.loading) return;
    this.loadMoreFoods();
  },

  // 加载食品数据
  async loadFoods() {
    this.setData({ loading: true });
    try {
      const db = wx.cloud.database();
      const res = await db
        .collection('foods')
        .orderBy('createdAt', 'desc')
        .limit(this.data.pageSize)
        .get();

      const foods = res.data.map((f) => ({
        ...f,
        categoryName:
          app.globalData.categories.find((c) => c.id === f.category)?.name ||
          '',
      }));

      this.setData({
        foods,
        allFoods: foods,
        filteredFoods: foods,
        hasMore: foods.length >= this.data.pageSize,
        loading: false,
      });
    } catch (err) {
      console.error('加载食品失败:', err);
      // 离线数据回退
      this.loadLocalFoods();
      this.setData({ loading: false });
    }
  },

  // 加载更多
  async loadMoreFoods() {
    this.setData({ loading: true });
    const { page, pageSize, activeCategory, searchKeyword, allFoods } =
      this.data;

    try {
      const db = wx.cloud.database();
      const res = await db
        .collection('foods')
        .orderBy('createdAt', 'desc')
        .skip(page * pageSize)
        .limit(pageSize)
        .get();

      const newFoods = res.data.map((f) => ({
        ...f,
        categoryName:
          app.globalData.categories.find((c) => c.id === f.category)?.name ||
          '',
      }));

      const foods = [...allFoods, ...newFoods];
      this.applyFilter(foods, activeCategory, searchKeyword);
      this.setData({
        allFoods: foods,
        page: page + 1,
        hasMore: newFoods.length >= pageSize,
        loading: false,
      });
    } catch (err) {
      console.error('加载更多失败:', err);
      this.setData({ hasMore: false, loading: false });
    }
  },

  // 加载本地数据（云开发未配置时）
  loadLocalFoods() {
    const seedData = require('../../../seed/seedData.js');
    const foods = seedData.default || seedData;
    this.setData({
      foods,
      allFoods: foods,
      filteredFoods: foods,
    });
  },

  // 切换分类
  onCategoryTap(e) {
    const { id } = e.currentTarget.dataset;
    const { allFoods, searchKeyword } = this.data;
    this.setData({ activeCategory: id });
    this.applyFilter(allFoods, id, searchKeyword);
  },

  // 搜索输入
  onSearchInput(e) {
    const keyword = e.detail.value;
    const { allFoods, activeCategory } = this.data;
    this.applyFilter(allFoods, activeCategory, keyword);
    this.setData({ searchKeyword: keyword });
  },

  // 应用筛选
  applyFilter(foods, category, keyword) {
    let result = foods;
    if (category && category !== 'all') {
      result = result.filter((f) => f.category === category);
    }
    if (keyword) {
      const kw = keyword.toLowerCase();
      result = result.filter(
        (f) =>
          f.name.toLowerCase().includes(kw) ||
          (f.desc && f.desc.toLowerCase().includes(kw))
      );
    }
    this.setData({ filteredFoods: result });
  },

  // 跳转分类页
  onCategoryMore(e) {
    const { id, name } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/category/category?id=${id}&name=${name}`,
    });
  },

  // 跳转详情页
  onFoodTap(e) {
    const { food } = e.detail;
    wx.navigateTo({
      url: `/pages/detail/detail?id=${food._id || food.id}`,
    });
  },

  // 快速加入购物车
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

    // 触发甜蜜动画
    util.showLoveAnimation(this);
    util.showToast('已加入购物车 ❤️');

    this.updateCartCount();
  },

  // 更新购物车角标
  updateCartCount() {
    const cart = app.globalData.cart || [];
    const count = cart.reduce((sum, item) => sum + item.quantity, 0);
    this.setData({ cartCount: count });
  },

  // 分享
  onShareAppMessage() {
    return {
      title: '情侣美食记 - 与TA一起享受美食时光 💕',
      path: '/pages/index/index',
    };
  },
});
