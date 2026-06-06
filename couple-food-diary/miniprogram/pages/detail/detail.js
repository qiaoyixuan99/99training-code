const app = getApp();
const util = require('../../utils/util.js');

Page({
  data: {
    foodId: '',
    food: null,
    isDouble: false,
    quantity: 1,
    currentImageIndex: 0,
    loveAnimations: [],
    showFullSteps: false,
  },

  onLoad(options) {
    const { id } = options;
    this.setData({ foodId: id });
    this.loadFoodDetail(id);
  },

  async loadFoodDetail(id) {
    util.showLoading('加载美食详情…');
    try {
      const db = wx.cloud.database();
      const res = await db.collection('foods').doc(id).get();
      const food = res.data;
      this.setData({
        food: {
          ...food,
          categoryName:
            app.globalData.categories.find((c) => c.id === food.category)
              ?.name || '',
          images: food.images || [food.image],
          steps: food.steps || [],
          nutrition: food.nutrition || {},
        },
      });
    } catch (err) {
      console.error('加载详情失败:', err);
      // 本地数据回退
      const seedData = require('../../../seed/seedData.js');
      const foods = seedData.default || seedData;
      const food = foods.find((f) => (f.id || f._id) === id);
      if (food) {
        this.setData({
          food: {
            ...food,
            categoryName:
              app.globalData.categories.find((c) => c.id === food.category)
                ?.name || '',
            images: food.images || [food.image],
            steps: food.steps || [],
            nutrition: food.nutrition || {},
          },
        });
      }
    }
    util.hideLoading();
  },

  // 切换图片
  onImageChange(e) {
    this.setData({ currentImageIndex: e.detail.current });
  },

  // 情侣双人份切换
  onDoubleToggle() {
    this.setData({ isDouble: !this.data.isDouble });
    util.showLoveAnimation(this);
  },

  // 数量增加
  onQuantityPlus() {
    this.setData({ quantity: this.data.quantity + 1 });
  },

  // 数量减少
  onQuantityMinus() {
    if (this.data.quantity > 1) {
      this.setData({ quantity: this.data.quantity - 1 });
    }
  },

  // 加入购物车
  onAddToCart() {
    const { food, isDouble, quantity } = this.data;
    if (!food) return;

    app.addToCart({
      foodId: food._id || food.id,
      name: food.name,
      image: food.image,
      price: food.price,
      calories: food.calories,
      category: food.category,
      isDouble,
      quantity,
    });

    util.showLoveAnimation(this);
    util.showToast(isDouble ? '情侣双人份已加入 💕' : '已加入购物车 ❤️');
  },

  // 立即购买
  onBuyNow() {
    const { food, isDouble, quantity } = this.data;
    if (!food) return;

    const orderItem = {
      foodId: food._id || food.id,
      name: food.name,
      image: food.image,
      price: food.price,
      calories: food.calories,
      category: food.category,
      isDouble,
      quantity,
    };

    wx.navigateTo({
      url: `/pages/order/order?item=${encodeURIComponent(JSON.stringify(orderItem))}`,
    });
  },

  // 展开/收起制作步骤
  onToggleSteps() {
    this.setData({ showFullSteps: !this.data.showFullSteps });
  },

  // 预览大图
  onPreviewImage() {
    const { food, currentImageIndex } = this.data;
    wx.previewImage({
      current: food.images[currentImageIndex],
      urls: food.images,
    });
  },

  // 计算双人份价格
  getDoublePrice() {
    const { food } = this.data;
    if (!food) return 0;
    return Math.round(food.price * 2 * 0.88 * 100) / 100;
  },

  onShareAppMessage() {
    const { food } = this.data;
    return {
      title: `${food ? food.name : '美食'} - 情侣美食记 💕`,
      path: `/pages/detail/detail?id=${this.data.foodId}`,
    };
  },
});
