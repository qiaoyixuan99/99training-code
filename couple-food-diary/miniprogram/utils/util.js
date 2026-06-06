/**
 * 情侣美食记 - 工具函数
 */

/**
 * 格式化日期为 YYYY-MM-DD
 */
const formatDate = (date) => {
  const d = date || new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

/**
 * 获取当前日期字符串
 */
const getToday = () => formatDate(new Date());

/**
 * 格式化时间戳为可读日期
 */
const formatTimestamp = (ts) => {
  const d = new Date(ts);
  return formatDate(d);
};

/**
 * 获取星期几（中文）
 */
const getWeekday = (dateStr) => {
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const d = new Date(dateStr);
  return weekdays[d.getDay()];
};

/**
 * Toast 提示（带甜蜜动画图标）
 */
const showToast = (title, icon = 'none', duration = 2000) => {
  wx.showToast({ title, icon, duration });
};

/**
 * 加载中提示
 */
const showLoading = (title = '加载中…') => {
  wx.showLoading({ title, mask: true });
};

const hideLoading = () => {
  wx.hideLoading();
};

/**
 * 确认弹窗
 */
const showConfirm = (content, title = '提示') => {
  return new Promise((resolve) => {
    wx.showModal({
      title,
      content,
      confirmColor: '#FF7EB3',
      success: (res) => resolve(res.confirm),
    });
  });
};

/**
 * 防抖
 */
const debounce = (fn, delay = 300) => {
  let timer = null;
  return function (...args) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
};

/**
 * 节流
 */
const throttle = (fn, delay = 300) => {
  let last = 0;
  return function (...args) {
    const now = Date.now();
    if (now - last >= delay) {
      last = now;
      fn.apply(this, args);
    }
  };
};

/**
 * 随机获取甜蜜提示文案
 */
const getLoveMessage = () => {
  const messages = [
    '❤️ 甜蜜加倍！',
    '💕 情侣份更优惠～',
    '🥰 用心为你准备！',
    '💝 爱与美食不可辜负',
    '🌸 每一口都是幸福',
    '✨ TA一定喜欢！',
    '💖 分享甜蜜时刻',
    '🎀 浪漫加分！',
  ];
  return messages[Math.floor(Math.random() * messages.length)];
};

/**
 * 计算情侣双人份价格（88折）
 */
const getDoublePrice = (price) => {
  return Math.round(price * 2 * 0.88 * 100) / 100;
};

/**
 * 触发甜蜜动画（浮起爱心）
 */
const showLoveAnimation = (that) => {
  if (!that) return;
  const id = `love_${Date.now()}`;
  const animations = that.data.loveAnimations || [];
  animations.push({
    id,
    text: getLoveMessage(),
    x: Math.random() * 200 + 100,
    y: Math.random() * 100 + 50,
  });
  that.setData({ loveAnimations: animations });
  setTimeout(() => {
    const list = that.data.loveAnimations || [];
    that.setData({
      loveAnimations: list.filter((a) => a.id !== id),
    });
  }, 1000);
};

module.exports = {
  formatDate,
  getToday,
  formatTimestamp,
  getWeekday,
  showToast,
  showLoading,
  hideLoading,
  showConfirm,
  debounce,
  throttle,
  getLoveMessage,
  getDoublePrice,
  showLoveAnimation,
};
