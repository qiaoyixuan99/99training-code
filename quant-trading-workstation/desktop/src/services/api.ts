/**
 * API 调用层 — 统一封装后端请求
 */
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  timeout: 30000,
});

// ── 行情数据 ──

export const marketApi = {
  getKline: (symbol: string, period = '1d', limit = 500) =>
    api.get(`/market/kline/${symbol}`, { params: { period, limit } }),

  getRealtime: (symbol: string) =>
    api.get(`/market/realtime/${symbol}`),

  getRealtimeBatch: (symbols: string[]) =>
    api.post('/market/realtime/batch', symbols),

  getStockList: (market = 'all') =>
    api.get('/market/stock-list', { params: { market } }),
};

// ── 缠论分析 ──

export const chanApi = {
  analyze: (symbol: string, period = '1d', startDate?: string, endDate?: string) =>
    api.post(`/chan-theory/analyze/${symbol}`, null, {
      params: { period, start_date: startDate, end_date: endDate },
    }),

  /** 批量多周期分析 — 一次请求分析多个时段 */
  batchAnalyze: (symbol: string, periods: string[]) =>
    api.post(`/chan-theory/batch-analyze/${symbol}`, { periods }),

  quick: (symbol: string, period = '1d') =>
    api.get(`/chan-theory/quick/${symbol}`, { params: { period } }),

  getPoints: (symbol: string, period = '1d') =>
    api.get(`/chan-theory/points/${symbol}`, { params: { period } }),

  getAnomalies: (symbol: string, period = '1d') =>
    api.get(`/chan-theory/anomalies/${symbol}`, { params: { period } }),

  getTurningPoints: (symbol: string, period = '1d') =>
    api.get(`/chan-theory/turning-points/${symbol}`, { params: { period } }),
};

// ── 选股 ──

export const screenerApi = {
  run: (conditions: Record<string, any>) =>
    api.post('/screener/run', conditions),

  getConditions: () =>
    api.get('/screener/conditions'),

  getTemplates: () =>
    api.get('/screener/templates'),
};

// ── 回测 ──

export const backtestApi = {
  run: (params: Record<string, any>) =>
    api.post('/backtest/run', params),

  getResult: (taskId: string) =>
    api.get(`/backtest/result/${taskId}`),

  getHistory: (limit = 20) =>
    api.get('/backtest/history', { params: { limit } }),
};

// ── 策略管理 ──

export const strategyApi = {
  list: () =>
    api.get('/strategy/list'),

  get: (id: number) =>
    api.get(`/strategy/${id}`),

  save: (strategy: Record<string, any>) =>
    api.post('/strategy/save', strategy),

  delete: (id: number) =>
    api.delete(`/strategy/${id}`),

  validate: (code: string) =>
    api.post('/strategy/validate', { code }),

  getTemplates: () =>
    api.get('/strategy/templates'),
};

// ── 动能评分 ──

export const momentumApi = {
  score: (symbol: string) =>
    api.post(`/momentum/score/${symbol}`),

  ranking: (industry?: string, limit = 20) =>
    api.get('/momentum/ranking', { params: { industry, limit } }),
};

// ── 大盘择时 ──

export const timingApi = {
  getSignal: (indexCode = 'sh.000001') =>
    api.get('/timing/signal', { params: { index_code: indexCode } }),

  getHistory: (indexCode = 'sh.000001', limit = 100) =>
    api.get('/timing/history', { params: { index_code: indexCode, limit } }),
};

// ── 自选股 ──

export const watchlistApi = {
  list: (group?: string) =>
    api.get('/watchlist/list', { params: { group } }),

  add: (item: Record<string, any>) =>
    api.post('/watchlist/add', item),

  remove: (symbol: string) =>
    api.delete(`/watchlist/remove/${symbol}`),

  getGroups: () =>
    api.get('/watchlist/groups'),
};

export default api;
