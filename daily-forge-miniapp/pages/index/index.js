// ──────────────────────────────────────
// Daily Forge — 主页逻辑
// 完整迁移自 app/index.html
// 微信小程序版：wx.Storage 替代 localStorage
//                setData 替代 DOM 操作
// ──────────────────────────────────────

const app = getApp();

// ── 常量定义 ──
const TASKS = [
  {
    id: 'morning',
    timeLabel: '🌅 上午 · 1h',
    timeClass: 'morning',
    title: '语法 + 泛听',
    descs: [
      'Cambridge Grammar for IELTS — 完成 1 个单元练习',
      'BBC World Service 泛听 15 分钟，保持语感',
    ],
    baseXP: 10,
    track: 'eng',
  },
  {
    id: 'noon',
    timeLabel: '☀️ 中午 · 20min',
    timeClass: 'noon',
    title: '词汇突击',
    descs: [
      'Anki 雅思核心词库：新词 15 个 + 旧词复习',
      '重点记忆昨日出错的词汇',
    ],
    baseXP: 5,
    track: 'eng',
  },
  {
    id: 'afternoon',
    timeLabel: '🌤️ 下午 · 1h',
    timeClass: 'afternoon',
    title: '英文技术精读',
    descs: [
      '精读 1 篇英文技术文章（AI/Agent 方向）',
      '拆解 3 个长难句，标注语法结构',
    ],
    baseXP: 10,
    track: 'both',
  },
  {
    id: 'evening',
    timeLabel: '🌙 晚上 · 1.5h',
    timeClass: 'evening',
    title: 'Agent 开发实战',
    descs: [
      'DeepLearning.AI LangChain 短课 / RAG 实战',
      '写代码，产出可运行的结果',
    ],
    baseXP: 20,
    track: 'agent',
  },
];

const REFLECTION_PROMPTS = [
  '今天这个时段，我搞懂了什么之前不懂的？',
  '用一句话总结刚才学到的核心概念：',
  '如果给一个完全不懂的人讲刚才学到的内容，我会怎么说？',
  '刚才学习中最让我兴奋的一个点是什么？',
  '今天遇到什么困难？我是怎么解决的（或打算怎么解决）？',
  '刚才学的东西，和我已有的知识有什么联系？',
];

const RANKS = [
  { level: 1, xp: 0, name: 'Prompt 学徒', icon: '🔰' },
  { level: 2, xp: 80, name: 'Grammar 工匠', icon: '📐' },
  { level: 3, xp: 180, name: 'RAG 探索者', icon: '🔍' },
  { level: 4, xp: 320, name: 'Vector 航海家', icon: '🧭' },
  { level: 5, xp: 500, name: 'Chain 编织者', icon: '⛓️' },
  { level: 6, xp: 720, name: 'Function 召唤师', icon: '🪄' },
  { level: 7, xp: 980, name: 'Agent 架构师', icon: '🏛️' },
  { level: 8, xp: 1300, name: 'Multi-Agent 指挥', icon: '🎭' },
  { level: 9, xp: 1680, name: 'LangGraph 塑造者', icon: '🧬' },
  { level: 10, xp: 2120, name: 'AI 工程师', icon: '⚡' },
  { level: 11, xp: 2620, name: 'LLM 驯兽师', icon: '🐉' },
  { level: 12, xp: 3200, name: '推理系统设计者', icon: '🧠' },
  { level: 13, xp: 3860, name: '双语 AI 先锋', icon: '🌐' },
  { level: 14, xp: 4600, name: '全栈 Agent 大师', icon: '👑' },
  { level: 15, xp: 5500, name: '第二职业就绪', icon: '🚀' },
];

const STORAGE_KEY = 'daily_forge_v1';

// ── 工具函数 ──
function todayStr() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function yesterdayStr() {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function getWeekBounds() {
  const now = new Date();
  const dayOfWeek = now.getDay();
  const monday = new Date(now);
  monday.setDate(now.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
  const days = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    days.push(`${y}-${m}-${day}`);
  }
  return days;
}

function getRank(xp) {
  for (let i = RANKS.length - 1; i >= 0; i--) {
    if (xp >= RANKS[i].xp) return RANKS[i];
  }
  return RANKS[0];
}

function getNextRank(xp) {
  for (let i = 0; i < RANKS.length; i++) {
    if (xp < RANKS[i].xp) return RANKS[i];
  }
  return null;
}

// ── 页面定义 ──
Page({
  data: {
    theme: 'dark',          // 当前主题 light/dark
    themeMode: 'auto',      // 主题模式 auto/light/dark
    dateDisplay: '',
    streak: 0,
    xp: 0,
    rank: { level: 1, name: 'Prompt 学徒', icon: '🔰' },
    nextRankName: 'Grammar 工匠',
    xpInLevel: 0,
    xpNeeded: 80,
    xpPercent: 0,
    xpRemain: 80,
    tasks: [],
    weekDays: [],
    viewMode: 'today',
    historyList: [],
    toast: { visible: false, msg: '', type: 'normal' },
    statsAnim: '',
    xpAnim: '',
    identityAnim: '',
  },

  // ── 内部状态（不参与渲染）──
  _state: null,
  _toastTimer: null,

  // ════════════════════════════════════
  // 生命周期
  // ════════════════════════════════════

  onLoad() {
    // 初始化主题
    const savedMode = wx.getStorageSync('themeMode') || 'auto';
    const theme = this.resolveTheme(savedMode);
    this.setData({ themeMode: savedMode, theme });
    this.syncPageColors(theme);

    // 加载数据
    this.loadState();
    this.render();

    // 入场动画
    setTimeout(() => this.playEntrance(), 100);
  },

  onShow() {
    // 每次显示页面时，检查系统主题是否变化
    if (this.data.themeMode === 'auto') {
      const theme = this.resolveTheme('auto');
      if (theme !== this.data.theme) {
        this.setData({ theme });
        this.syncPageColors(theme);
      }
    }
    // 日切后刷新数据
    this.loadState();
    this.render();
  },

  // ════════════════════════════════════
  // 主题管理
  // ════════════════════════════════════

  /**
   * 根据模式解析主题
   */
  resolveTheme(mode) {
    if (mode === 'auto') {
      const sysInfo = wx.getSystemInfoSync();
      return sysInfo.theme || 'dark';
    }
    return mode;
  },

  /**
   * 同步页面级主题色（导航栏 + 背景），消除闪烁
   */
  syncPageColors(theme) {
    const isLight = theme === 'light';
    wx.setNavigationBarColor({
      frontColor: isLight ? '#000000' : '#ffffff',
      backgroundColor: isLight ? '#f5f5f7' : '#0f1117',
    });
    wx.setBackgroundColor({
      backgroundColor: isLight ? '#f5f5f7' : '#0f1117',
    });
  },

  /**
   * 循环切换主题：dark → light → auto → dark
   */
  cycleTheme() {
    const modes = ['dark', 'light', 'auto'];
    const currentIdx = modes.indexOf(this.data.themeMode);
    const nextMode = modes[(currentIdx + 1) % modes.length];
    const theme = this.resolveTheme(nextMode);

    wx.setStorageSync('themeMode', nextMode);
    this.setData({ themeMode: nextMode, theme });
    this.syncPageColors(theme);

    // 同步到全局 App
    if (app && app.setThemeMode) {
      app.setThemeMode(nextMode);
    }

    const labels = { dark: '🌙 黑夜模式', light: '☀️ 白天模式', auto: '🔄 跟随系统' };
    this.showToast(labels[nextMode], 'normal', 1500);
  },

  // ════════════════════════════════════
  // 数据持久化
  // ════════════════════════════════════

  loadState() {
    try {
      const raw = wx.getStorageSync(STORAGE_KEY);
      if (raw) {
        this._state = JSON.parse(raw);
      } else {
        this._state = {
          xp: 0,
          streak: 0,
          lastCompletedDate: null,
          daily: {},
          weeklyReflections: {},
        };
      }
    } catch (e) {
      this._state = {
        xp: 0,
        streak: 0,
        lastCompletedDate: null,
        daily: {},
        weeklyReflections: {},
      };
    }
  },

  saveState() {
    try {
      wx.setStorageSync(STORAGE_KEY, JSON.stringify(this._state));
    } catch (e) {
      console.error('保存失败:', e);
    }
  },

  // ════════════════════════════════════
  // 连续天数逻辑
  // ════════════════════════════════════

  updateStreak() {
    const s = this._state;
    const today = todayStr();
    const yesterday = yesterdayStr();
    const todayTasks = s.daily[today];
    const allDoneToday = todayTasks && TASKS.every(t => todayTasks[t.id]?.done);

    if (allDoneToday) {
      if (s.lastCompletedDate === yesterday || s.lastCompletedDate === today) {
        // 连续中
      } else if (s.lastCompletedDate && s.lastCompletedDate !== yesterday && s.lastCompletedDate !== today) {
        s.streak = 0;
      }
      if (s.lastCompletedDate !== today) {
        s.streak = (s.streak || 0) + 1;
        s.lastCompletedDate = today;
      }
    } else if (!allDoneToday && s.lastCompletedDate && s.lastCompletedDate !== today && s.lastCompletedDate !== yesterday) {
      s.streak = 0;
    }
  },

  // ════════════════════════════════════
  // 渲染
  // ════════════════════════════════════

  render() {
    this.updateStreak();
    this.saveState();

    const s = this._state;
    const today = todayStr();
    const now = new Date();
    const rank = getRank(s.xp);
    const nextRank = getNextRank(s.xp);
    const dayNames = ['日', '一', '二', '三', '四', '五', '六'];

    // 日期显示
    const dateDisplay = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 周${dayNames[now.getDay()]}`;

    // XP 计算
    let xpInLevel, xpNeeded;
    if (nextRank) {
      xpInLevel = s.xp - rank.xp;
      xpNeeded = nextRank.xp - rank.xp;
    } else {
      xpInLevel = s.xp - rank.xp;
      xpNeeded = 500;
    }
    const xpPercent = Math.min(100, Math.round((xpInLevel / xpNeeded) * 100));
    const xpRemain = nextRank ? nextRank.xp - s.xp : 0;

    // 组装任务数据
    const todayTasks = s.daily[today] || {};
    const tasks = TASKS.map((task, i) => {
      const td = todayTasks[task.id] || { done: false, reflect: '', bonus: 0 };
      const reflectIdx = (i + now.getDate()) % REFLECTION_PROMPTS.length;
      return {
        ...task,
        completed: td.done,
        reflect: td.reflect || '',
        bonus: td.bonus || 0,
        prompt: REFLECTION_PROMPTS[reflectIdx],
        animClass: '',
      };
    });

    // 本周网格
    const weekDayNames = ['一', '二', '三', '四', '五', '六', '日'];
    const weekDates = getWeekBounds();
    const weekDays = weekDates.map((d, i) => {
      const dd = s.daily[d];
      const allDone = dd && TASKS.every(t => dd[t.id]?.done);
      const partial = dd && TASKS.some(t => dd[t.id]?.done);
      let dotClass = 'none';
      if (allDone) dotClass = 'all-done';
      else if (partial) dotClass = 'partial';
      return {
        date: d,
        dayName: weekDayNames[i],
        displayDate: d.slice(5),
        isToday: d === today,
        allDone,
        dotClass,
      };
    });

    this.setData({
      dateDisplay,
      streak: s.streak,
      xp: s.xp,
      rank,
      nextRankName: nextRank ? nextRank.icon + ' ' + nextRank.name : '👑 终极',
      xpInLevel,
      xpNeeded,
      xpPercent,
      xpRemain,
      tasks,
      weekDays,
    });

    // 如果当前是历史视图，刷新历史
    if (this.data.viewMode === 'history') {
      this.renderHistory();
    }
  },

  // ════════════════════════════════════
  // 任务操作
  // ════════════════════════════════════

  /**
   * 完成打卡
   */
  completeTask(e) {
    const taskId = e.currentTarget.dataset.id;
    const task = TASKS.find(t => t.id === taskId);
    if (!task) return;

    const s = this._state;
    const today = todayStr();
    if (!s.daily[today]) s.daily[today] = {};

    // 变量奖励：10% 概率触发 2-3x 暴击
    const roll = Math.random();
    let multiplier = 1;
    let toastType = 'normal';
    let toastMsg = '';

    if (roll < 0.10) {
      multiplier = Math.random() < 0.5 ? 3 : 2;
      toastType = 'crit';
      toastMsg = `🎯 暴击! ${multiplier}x XP! +${task.baseXP * multiplier} XP`;
    } else {
      toastMsg = `✅ +${task.baseXP} XP`;
    }

    const bonus = task.baseXP * (multiplier - 1);
    const earned = task.baseXP * multiplier;

    s.daily[today][taskId] = { done: true, reflect: '', bonus };
    s.xp += earned;

    // 检查今日是否全部完成
    const allDone = TASKS.every(t => {
      if (t.id === taskId) return true;
      return s.daily[today][t.id]?.done;
    });

    this.updateStreak();

    // 全完成且每 7 天连续奖励
    if (allDone && s.streak > 0 && s.streak % 7 === 0) {
      const streakBonus = 50;
      s.xp += streakBonus;
      this.saveState();
      this.render();
      this.showToast(`🔥 连续 ${s.streak} 天! 额外 +${streakBonus} XP`, 'streak-bonus', 3000);
      return;
    }

    // 检查升级
    const oldRank = getRank(s.xp - earned);
    const newRank = getRank(s.xp);
    if (newRank.level > oldRank.level) {
      this.saveState();
      this.render();
      this.showToast(toastMsg, toastType, 2500);
      setTimeout(() => {
        this.showToast(`⬆️ 升级! ${newRank.icon} ${newRank.name}`, 'level-up', 3500);
      }, 600);
      return;
    }

    this.saveState();
    this.render();
    this.showToast(toastMsg, toastType, 2500);
  },

  /**
   * 反思输入事件 — 同步更新 storage + data
   */
  onReflectInput(e) {
    const taskId = e.currentTarget.dataset.id;
    const value = e.detail.value;

    // 1. 更新持久化层
    const s = this._state;
    const today = todayStr();
    if (!s.daily[today]) s.daily[today] = {};
    if (!s.daily[today][taskId]) s.daily[today][taskId] = { done: true, reflect: '', bonus: 0 };
    s.daily[today][taskId].reflect = value;

    // 2. 更新视图层 tasks 数组，确保 textarea 正确显示
    const tasks = this.data.tasks.map(t => {
      if (t.id === taskId) return { ...t, reflect: value };
      return t;
    });
    this.setData({ tasks });
  },

  /**
   * 保存反思 — 数据已在输入时实时写入，此处持久化到 Storage
   */
  saveReflection(e) {
    this.saveState();
    this.showToast('💾 反思已保存', 'normal', 1800);
  },

  /**
   * 撤销任务
   */
  undoTask(e) {
    const taskId = e.currentTarget.dataset.id;
    const s = this._state;
    const today = todayStr();
    if (!s.daily[today] || !s.daily[today][taskId]) return;

    const bonus = s.daily[today][taskId].bonus || 0;
    const task = TASKS.find(t => t.id === taskId);
    if (!task) return;

    s.xp -= (task.baseXP + bonus);
    // 确保 XP 不为负
    if (s.xp < 0) s.xp = 0;

    delete s.daily[today][taskId];
    this.updateStreak();
    this.saveState();
    this.render();
    this.showToast('↩ 已撤销', 'normal', 1500);
  },

  // ════════════════════════════════════
  // 视图切换
  // ════════════════════════════════════

  switchToToday() {
    this.setData({ viewMode: 'today' });
  },

  switchToHistory() {
    this.renderHistory();
    this.setData({ viewMode: 'history' });
  },

  // ════════════════════════════════════
  // 历史记录渲染
  // ════════════════════════════════════

  renderHistory() {
    const s = this._state;
    const dates = Object.keys(s.daily).sort().reverse().slice(0, 14);

    if (dates.length === 0) {
      this.setData({ historyList: [] });
      return;
    }

    const historyList = dates.map(d => {
      const dd = s.daily[d];
      const engDone = [dd.morning, dd.noon].every(t => t?.done);
      const agentDone = dd.evening?.done;
      const allDone = TASKS.every(t => dd[t.id]?.done);

      const dayXP = TASKS.reduce((sum, t) => {
        if (dd[t.id]?.done) return sum + t.baseXP + (dd[t.id].bonus || 0);
        return sum;
      }, 0);

      const reflection = TASKS
        .map(t => dd[t.id]?.reflect)
        .filter(Boolean)
        .join(' | ') || '—';

      const [y, m, day] = d.split('-');
      return {
        date: d,
        dateStr: `${y}年${m}月${day}日`,
        dayXP,
        reflection: reflection.slice(0, 80) + (reflection.length > 80 ? '...' : ''),
        allDone,
        engDone,
        agentDone,
      };
    });

    this.setData({ historyList });
  },

  // ════════════════════════════════════
  // Toast 提示
  // ════════════════════════════════════

  showToast(msg, type, duration) {
    // 清除上一个 toast 计时器
    if (this._toastTimer) {
      clearTimeout(this._toastTimer);
    }

    this.setData({
      toast: { visible: true, msg, type },
    });

    this._toastTimer = setTimeout(() => {
      this.setData({
        'toast.visible': false,
      });
    }, duration || 2500);
  },

  // ════════════════════════════════════
  // 任务详情导航
  // ════════════════════════════════════

  openTaskDetail(e) {
    const taskId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/detail/detail?id=${taskId}`,
    });
  },

  noop() {},

  // ════════════════════════════════════
  // 入场动画（类 GSAP stagger 效果）
  // ════════════════════════════════════

  playEntrance() {
    // 使用 CSS 类驱动动画，逐个延迟显示
    const tasks = this.data.tasks.map((t, i) => ({
      ...t,
      animClass: '',
    }));
    this.setData({ tasks });

    // stagger 效果：每张卡片延迟 100ms 出现
    tasks.forEach((t, i) => {
      setTimeout(() => {
        const key = `tasks[${i}].animClass`;
        this.setData({ [key]: 'card-enter' });
      }, i * 120);
    });

    // 统计卡片弹入
    setTimeout(() => this.setData({ statsAnim: 'stats-enter' }), 50);
    // XP 进度条
    setTimeout(() => this.setData({ xpAnim: 'xp-enter' }), 350);
    // 身份横幅
    setTimeout(() => this.setData({ identityAnim: 'identity-enter' }), 500);
  },

  // ════════════════════════════════════
  // 重置
  // ════════════════════════════════════

  resetAll() {
    wx.showModal({
      title: '确认重置',
      content: '确定要清除所有学习记录吗？此操作不可恢复。',
      success: (res) => {
        if (res.confirm) {
          this._state = {
            xp: 0,
            streak: 0,
            lastCompletedDate: null,
            daily: {},
            weeklyReflections: {},
          };
          this.saveState();
          this.render();
          this.showToast('🔄 已重置，重新出发!', 'normal', 2000);
        }
      },
    });
  },
});
