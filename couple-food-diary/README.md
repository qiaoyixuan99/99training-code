# 💕 情侣美食记 - 微信小程序

情侣专属美食小程序，涵盖美食浏览、购物车和饮食日记三大核心模块。

## 功能概览

### 🍽️ 美食浏览
- 首页横向分类栏：主食、零食、水果、饮料、奶茶、沙拉、汤品 7大类
- 每类15-20种食品，共**120种**预置食品数据
- 搜索、分类筛选、排序（价格/卡路里）
- 食品详情页：图片轮播、营养成分、制作步骤

### 🛒 购物车
- 加入购物车 / 情侣双人份（88折优惠）
- 数量修改、删除、情侣份切换
- 模拟下单流程

### 📖 饮食日记
- 按日期展示三餐+零食记录
- 每日卡路里统计与进度条
- 7天摄入趋势柱状图
- 下单后自动同步到日记

### 🔧 管理后台
- 管理员密码登录
- 食品增删改查
- 图片上传（云存储）
- 批量JSON导入

## 技术栈

- **框架**：微信小程序原生
- **后端**：微信云开发（CloudBase）
- **数据库**：云数据库（foods, carts, orders, diary）
- **存储**：云存储（食品图片）
- **计算**：云函数（CRUD操作）

## 项目结构

```
couple-food-diary/
├── miniprogram/              # 小程序前端
│   ├── app.js/json/wxss      # 应用入口
│   ├── components/           # 组件
│   │   ├── food-card/        # 食品卡片
│   │   └── cart-badge/       # 购物车角标
│   ├── pages/
│   │   ├── index/            # 首页（美食浏览）
│   │   ├── category/         # 分类列表
│   │   ├── detail/           # 食品详情
│   │   ├── cart/             # 购物车
│   │   ├── order/            # 确认订单
│   │   ├── diary/            # 饮食日记
│   │   └── admin/            # 管理后台
│   └── utils/util.js         # 工具函数
├── cloudfunctions/           # 云函数
│   ├── getFoods/             # 获取食品列表
│   ├── getFoodDetail/        # 获取食品详情
│   ├── addToCart/            # 加入购物车
│   ├── updateCart/           # 更新购物车
│   ├── placeOrder/           # 下单+同步日记
│   ├── getDiary/             # 获取日记
│   ├── adminAddFood/         # 添加食品
│   ├── adminUpdateFood/      # 更新食品
│   ├── adminDeleteFood/      # 删除食品
│   └── adminBatchImport/     # 批量导入
├── seed/
│   └── seedData.js           # 120种预置食品数据
└── project.config.json
```

## 快速开始

### 1. 准备工作
- 注册[微信小程序](https://mp.weixin.qq.com)，获取 AppID
- 开通云开发环境

### 2. 配置项目
1. 修改 `project.config.json` 中的 `appid` 为你的 AppID
2. 修改 `miniprogram/app.js` 中 `wx.cloud.init` 的 `env` 为你的云环境ID

### 3. 导入项目
1. 打开微信开发者工具
2. 导入项目，选择 `couple-food-diary` 目录
3. AppID 填写你的小程序 AppID

### 4. 部署云函数
1. 在开发者工具中右键每个云函数目录
2. 选择「上传并部署：云端安装依赖」

### 5. 初始化数据库
1. 在云开发控制台创建集合：`foods`, `carts`, `orders`, `diary`
2. 在管理后台「批量导入」Tab 粘贴 `seed/seedData.js` 中的数组数据
3. 或使用云函数 `adminBatchImport` 导入

### 6. Tab Bar 图标
将40x40像素的PNG图标放入 `miniprogram/images/` 目录：
- `tab-food.png` / `tab-food-active.png`
- `tab-cart.png` / `tab-cart-active.png`
- `tab-diary.png` / `tab-diary-active.png`
- `tab-admin.png` / `tab-admin-active.png`

可使用 [iconfont](https://www.iconfont.cn) 下载对应图标。

## UI设计

- **主色调**：#FF7EB3（粉色系）
- **辅助色**：#FFB3CC、#FFE0EC、#E8609A
- **背景色**：#FFF0F5
- **风格**：圆角卡片、渐变按钮、甜蜜动画

## 管理员密码

默认密码：`foodie2024`
（可在 `pages/admin/admin.js` 中修改）

## 数据说明

种子数据使用 Unsplash 真实食物图片 URL，所有数据包含：
- 名称、分类、价格、卡路里
- 营养成分（蛋白质、脂肪、碳水、纤维）
- 制作步骤
- 多张图片

## License

MIT
