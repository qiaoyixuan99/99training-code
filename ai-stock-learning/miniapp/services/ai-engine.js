// AI分析引擎 API 服务
// 对接 Python ai-engine 的 Flask 服务器

const API_BASE = 'http://127.0.0.1:5000';

/**
 * 调用 Python 引擎进行K线综合分析
 * @param {Object} options - { code, period, count }
 * @returns {Promise<Object>} 完整分析报告
 */
function fetchAnalysis(options = {}) {
  const { code = '000001', period = 'day', count = 200 } = options;

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}/api/analyze`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { code, period, count },
      timeout: 15000,  // 分析可能较慢，给15秒
      success(res) {
        if (res.statusCode === 200 && res.data && res.data.success) {
          resolve(res.data.data);
        } else {
          reject(new Error(res.data?.error || '分析请求失败'));
        }
      },
      fail(err) {
        reject(new Error(`无法连接AI引擎: ${err.errMsg}`));
      }
    });
  });
}

/**
 * 轻量分析 — 只返回摘要（适合列表快速展示）
 */
function fetchSimpleAnalysis(code, period = 'day') {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}/api/analyze_simple`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { code, period },
      timeout: 10000,
      success(res) {
        if (res.statusCode === 200 && res.data && res.data.success) {
          resolve(res.data.data);
        } else {
          reject(new Error(res.data?.error || '请求失败'));
        }
      },
      fail(err) {
        reject(new Error(`无法连接AI引擎: ${err.errMsg}`));
      }
    });
  });
}

/**
 * 获取实时行情
 */
function fetchQuote(code) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}/api/quote`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { code },
      timeout: 8000,
      success(res) {
        if (res.statusCode === 200 && res.data && res.data.success) {
          resolve(res.data.data);
        } else {
          reject(new Error(res.data?.error || '请求失败'));
        }
      },
      fail(err) {
        reject(new Error(`无法连接AI引擎: ${err.errMsg}`));
      }
    });
  });
}

/**
 * 搜索股票
 */
function searchStock(keyword) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}/api/search`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { keyword },
      timeout: 8000,
      success(res) {
        if (res.statusCode === 200 && res.data && res.data.success) {
          resolve(res.data.data);
        } else {
          reject(new Error(res.data?.error || '搜索失败'));
        }
      },
      fail(err) {
        reject(new Error(`无法连接AI引擎: ${err.errMsg}`));
      }
    });
  });
}

/**
 * 发送本地已获取的K线数据到引擎进行分析（绕过Python→东方财富连接问题）
 * @param {Object} options - { code, period, klines, stockName, latestPrice, latestChangePct }
 * @returns {Promise<Object>} 完整分析报告
 */
function fetchAnalysisWithData(options = {}) {
  const {
    code = '000001',
    period = 'day',
    klines = [],
    stockName = '',
    latestPrice,
    latestChangePct,
  } = options;

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${API_BASE}/api/analyze_data`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: {
        code,
        period,
        klines,
        stock_name: stockName,
        latest_price: latestPrice,
        latest_change_pct: latestChangePct,
      },
      timeout: 20000,
      success(res) {
        if (res.statusCode === 200 && res.data && res.data.success) {
          resolve(res.data.data);
        } else {
          reject(new Error(res.data?.error || '分析请求失败'));
        }
      },
      fail(err) {
        reject(new Error(`无法连接AI引擎: ${err.errMsg}`));
      }
    });
  });
}

/**
 * 健康检查 — 验证引擎是否在线
 */
function ping() {
  return new Promise((resolve) => {
    wx.request({
      url: `${API_BASE}/api/health`,
      method: 'GET',
      timeout: 3000,
      success(res) {
        if (res.statusCode === 200 && res.data?.status === 'ok') {
          resolve({
            online: true,
            strategies: res.data.strategies || [],
            predictors: res.data.predictors || [],
          });
        } else {
          resolve({ online: false });
        }
      },
      fail() {
        resolve({ online: false });
      }
    });
  });
}

module.exports = {
  API_BASE,
  fetchAnalysis,
  fetchAnalysisWithData,
  fetchSimpleAnalysis,
  fetchQuote,
  searchStock,
  ping,
};
