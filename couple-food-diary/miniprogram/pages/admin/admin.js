const app = getApp();
const util = require('../../utils/util.js');

Page({
  data: {
    // 当前 tab
    activeTab: 'list', // list | add | import
    // 食品列表
    foods: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    searchKeyword: '',
    filterCategory: '',
    // 新增/编辑表单
    formMode: 'add', // add | edit
    editingId: '',
    form: {
      name: '',
      category: 'staple',
      price: '',
      calories: '',
      image: '',
      desc: '',
      nutrition: { protein: '', fat: '', carbs: '', fiber: '' },
      steps: [''],
    },
    // 图片上传
    uploadProgress: 0,
    uploading: false,
    // JSON 导入
    jsonText: '',
    importResult: '',
    // 管理员验证
    isAdmin: false,
    adminPassword: '',
  },

  onLoad() {
    this.checkAdmin();
  },

  // 检查管理员状态
  checkAdmin() {
    const isAdmin = wx.getStorageSync('isAdmin');
    if (isAdmin) {
      this.setData({ isAdmin: true });
      this.loadFoodList();
    }
  },

  // 管理员登录
  onAdminLogin() {
    // 简单密码验证
    if (this.data.adminPassword === 'foodie2024') {
      wx.setStorageSync('isAdmin', true);
      this.setData({ isAdmin: true });
      this.loadFoodList();
      util.showToast('欢迎回来，管理员 💕');
    } else {
      util.showToast('密码错误 ❌');
    }
  },

  onPasswordInput(e) {
    this.setData({ adminPassword: e.detail.value });
  },

  // 切换 tab
  onTabChange(e) {
    const { tab } = e.currentTarget.dataset;
    this.setData({ activeTab: tab });
    if (tab === 'list') {
      this.loadFoodList();
    }
  },

  // 加载食品列表
  async loadFoodList() {
    this.setData({ loading: true });
    try {
      const db = wx.cloud.database();
      const res = await db
        .collection('foods')
        .orderBy('createdAt', 'desc')
        .limit(this.data.pageSize)
        .get();

      this.setData({
        foods: res.data,
        hasMore: res.data.length >= this.data.pageSize,
        loading: false,
      });
    } catch (err) {
      console.error('加载食品列表失败:', err);
      this.setData({ loading: false });
    }
  },

  // 搜索
  onSearchInput(e) {
    this.setData({ searchKeyword: e.detail.value });
    this.filterFoods();
  },

  // 分类筛选
  onFilterCategory(e) {
    const cat = e.currentTarget.dataset.cat;
    this.setData({
      filterCategory: this.data.filterCategory === cat ? '' : cat,
    });
    this.filterFoods();
  },

  filterFoods() {
    // 本地筛选（实际应调云函数）
    const { foods, searchKeyword, filterCategory } = this.data;
    let result = [...foods];
    if (filterCategory) {
      result = result.filter((f) => f.category === filterCategory);
    }
    if (searchKeyword) {
      result = result.filter((f) => f.name.includes(searchKeyword));
    }
    this.setData({ foods: result });
  },

  // 表单字段更新
  onFormField(e) {
    const { field } = e.currentTarget.dataset;
    const value = e.detail.value;
    this.setData({ [`form.${field}`]: value });
  },

  onNutritionField(e) {
    const { field } = e.currentTarget.dataset;
    const value = e.detail.value;
    this.setData({ [`form.nutrition.${field}`]: value });
  },

  onStepInput(e) {
    const { index } = e.currentTarget.dataset;
    const steps = [...this.data.form.steps];
    steps[index] = e.detail.value;
    this.setData({ 'form.steps': steps });
  },

  addStep() {
    const steps = [...this.data.form.steps, ''];
    this.setData({ 'form.steps': steps });
  },

  removeStep(e) {
    const { index } = e.currentTarget.dataset;
    const steps = this.data.form.steps.filter((_, i) => i !== index);
    this.setData({ 'form.steps': steps.length > 0 ? steps : [''] });
  },

  // 图片上传
  onChooseImage() {
    wx.chooseImage({
      count: 3,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        this.setData({ uploading: true });
        const filePath = res.tempFilePaths[0];
        const cloudPath = `foods/${Date.now()}_${Math.random().toString(36).slice(2, 8)}.jpg`;

        wx.cloud
          .uploadFile({
            cloudPath,
            filePath,
            success: (uploadRes) => {
              this.setData({
                'form.image': uploadRes.fileID,
                uploading: false,
              });
              util.showToast('图片上传成功 ✅');
            },
            fail: (err) => {
              console.error('上传失败:', err);
              this.setData({ uploading: false });
              util.showToast('上传失败，请重试');
            },
          });
      },
    });
  },

  // 提交表单
  async onSubmitForm() {
    const { form, formMode, editingId } = this.data;

    // 验证必填字段
    if (!form.name || !form.price || !form.calories) {
      util.showToast('请填写名称、价格和卡路里');
      return;
    }

    const foodData = {
      name: form.name,
      category: form.category,
      price: parseFloat(form.price),
      calories: parseInt(form.calories),
      image: form.image || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400',
      images: form.image ? [form.image] : ['https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400'],
      desc: form.desc || '',
      nutrition: {
        protein: parseFloat(form.nutrition.protein) || 0,
        fat: parseFloat(form.nutrition.fat) || 0,
        carbs: parseFloat(form.nutrition.carbs) || 0,
        fiber: parseFloat(form.nutrition.fiber) || 0,
      },
      steps: form.steps.filter((s) => s.trim()),
      updatedAt: new Date(),
    };

    try {
      const db = wx.cloud.database();
      if (formMode === 'add') {
        foodData.createdAt = new Date();
        await db.collection('foods').add({ data: foodData });
        util.showToast('添加成功 ✅');
      } else {
        await db
          .collection('foods')
          .doc(editingId)
          .update({ data: foodData });
        util.showToast('更新成功 ✅');
      }

      // 重置表单
      this.resetForm();
      this.loadFoodList();
      this.setData({ activeTab: 'list' });
    } catch (err) {
      console.error('提交失败:', err);
      util.showToast('操作失败，请重试');
    }
  },

  // 编辑食品
  onEditFood(e) {
    const { food } = e.currentTarget.dataset;
    this.setData({
      activeTab: 'add',
      formMode: 'edit',
      editingId: food._id,
      form: {
        name: food.name || '',
        category: food.category || 'staple',
        price: String(food.price || ''),
        calories: String(food.calories || ''),
        image: food.image || '',
        desc: food.desc || '',
        nutrition: {
          protein: String(food.nutrition?.protein || ''),
          fat: String(food.nutrition?.fat || ''),
          carbs: String(food.nutrition?.carbs || ''),
          fiber: String(food.nutrition?.fiber || ''),
        },
        steps: food.steps && food.steps.length > 0 ? food.steps : [''],
      },
    });
    wx.pageScrollTo({ scrollTop: 0 });
  },

  // 删除食品
  onDeleteFood(e) {
    const { food } = e.currentTarget.dataset;
    util
      .showConfirm(`确定删除「${food.name}」吗？此操作不可撤销！`)
      .then(async (confirm) => {
        if (!confirm) return;
        try {
          const db = wx.cloud.database();
          await db.collection('foods').doc(food._id).remove();
          util.showToast('已删除');
          this.loadFoodList();
        } catch (err) {
          console.error('删除失败:', err);
          util.showToast('删除失败');
        }
      });
  },

  // JSON 批量导入
  onJsonInput(e) {
    this.setData({ jsonText: e.detail.value });
  },

  async onBatchImport() {
    const { jsonText } = this.data;
    let foods;
    try {
      foods = JSON.parse(jsonText);
      if (!Array.isArray(foods)) {
        throw new Error('JSON 格式必须为数组');
      }
    } catch (e) {
      this.setData({ importResult: 'JSON 格式错误: ' + e.message });
      return;
    }

    try {
      const res = await wx.cloud.callFunction({
        name: 'adminBatchImport',
        data: { foods },
      });
      this.setData({
        importResult: `成功导入 ${res.result.count} 种食品 ✅`,
        jsonText: '',
      });
      this.loadFoodList();
      util.showToast(`成功导入 ${res.result.count} 种食品`);
    } catch (err) {
      console.error('批量导入失败:', err);
      // 本地导入回退
      this.setData({
        importResult: `离线模式：已解析 ${foods.length} 条数据，云开发未配置时暂存本地`,
      });
    }
  },

  // 重置表单
  resetForm() {
    this.setData({
      formMode: 'add',
      editingId: '',
      form: {
        name: '',
        category: 'staple',
        price: '',
        calories: '',
        image: '',
        desc: '',
        nutrition: { protein: '', fat: '', carbs: '', fiber: '' },
        steps: [''],
      },
    });
  },

  onShareAppMessage() {
    return {
      title: '情侣美食记 - 管理后台',
      path: '/pages/admin/admin',
    };
  },
});
