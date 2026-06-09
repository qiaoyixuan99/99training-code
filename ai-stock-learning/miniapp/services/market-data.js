// 实时行情数据服务
// 数据源：东方财富 API（免费、稳定、无需token）
// 降级：API不可用时自动使用本地示例数据

const mockData = require('./mock-data');

const API = {
  // K线数据（历史）
  KLINE: 'https://push2his.eastmoney.com/api/qt/stock/kline/get',
  // 实时行情
  QUOTE: 'https://push2.eastmoney.com/api/qt/stock/get',
  // 股票搜索
  SEARCH: 'https://searchadapter.eastmoney.com/api/suggest/get',
};

// K线周期映射
const PERIOD_MAP = {
  '5min':   '5',
  '15min':  '15',
  '30min':  '30',
  '60min':  '60',
  'day':    '101',
  'week':   '102',
  'month':  '103',
};

// 市场代码
function getSecid(code) {
  if (!code || typeof code !== 'string') return '0.000001';
  if (code.startsWith('6')) return `1.${code}`;  // 上海
  if (code.startsWith('0') || code.startsWith('3')) return `0.${code}`; // 深圳
  if (code.startsWith('00')) return `0.${code}`;  // 深圳
  return `0.${code}`;
}

function getMarketCode(code) {
  if (!code || typeof code !== 'string') return 0;
  if (code.startsWith('6')) return 1;  // sh
  return 0; // sz
}

/**
 * 获取K线数据
 * @param {string} code - 股票代码
 * @param {string} period - 周期 (day/week/month/60min/30min/15min/5min)
 * @param {number} count - 获取条数，默认200
 */
function fetchKlineData(code, period = 'day', count = 200) {
  if (!code) return Promise.reject(new Error('股票代码无效'));
  const secid = getSecid(code);
  const klt = PERIOD_MAP[period] || '101';

  return new Promise((resolve, reject) => {
    wx.request({
      url: API.KLINE,
      timeout: 5000,  // 5秒超时，快速降级到mock
      data: {
        secid: secid,
        klt: klt,
        fqt: 1,
        beg: '0',
        end: '20500000',
        lmt: count,
        fields1: 'f1,f2,f3,f4,f5,f6',
        fields2: 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61'
      },
      success(res) {
        if (res.data && res.data.data) {
          const result = parseKlineData(res.data.data, code, secid);
          resolve(result);
        } else {
          // API返回格式异常 → 降级到示例数据
          console.warn('K线API返回异常，使用示例数据');
          resolve(mockData.getSampleKlines(code, period));
        }
      },
      fail(err) {
        // 网络请求失败 → 降级到示例数据
        console.warn('K线API请求失败，使用示例数据:', err.errMsg);
        resolve(mockData.getSampleKlines(code, period));
      }
    });
  });
}

/**
 * 解析K线数据
 * 返回格式: [{ time, open, close, high, low, volume, amount, amplitude, changePct, change, turnover }]
 */
function parseKlineData(data, code, secid) {
  const { klines = [], name = '' } = data;

  const list = klines.map(line => {
    const parts = line.split(',');
    return {
      time: parts[0],           // 日期
      open: parseFloat(parts[1]),
      close: parseFloat(parts[2]),
      high: parseFloat(parts[3]),
      low: parseFloat(parts[4]),
      volume: parseFloat(parts[5]),
      amount: parseFloat(parts[6]),
      amplitude: parseFloat(parts[7]) || 0,      // 振幅
      changePct: parseFloat(parts[8]) || 0,      // 涨跌幅
      change: parseFloat(parts[9]) || 0,         // 涨跌额
      turnover: parseFloat(parts[10]) || 0,      // 换手率
    };
  });

  return {
    code,
    name,
    secid,
    klines: list,
    count: list.length,
    latest: list[list.length - 1] || null,
  };
}

/**
 * 获取实时行情快照
 */
function fetchQuote(code) {
  if (!code) return Promise.reject(new Error('股票代码无效'));
  const secid = getSecid(code);

  return new Promise((resolve) => {
    wx.request({
      url: API.QUOTE,
      timeout: 5000,
      data: {
        secid: secid,
        fields: 'f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f171'
      },
      success(res) {
        if (res.data && res.data.data) {
          const d = res.data.data;
          resolve({
            code,
            name: d.f58 || '',
            price: d.f43 / 100 || 0,
            high: d.f44 / 100 || 0,
            low: d.f45 / 100 || 0,
            open: d.f46 / 100 || 0,
            volume: d.f47 || 0,
            amount: d.f48 || 0,
            change: d.f169 / 100 || 0,
            changePct: d.f170 / 100 || 0,
            turnover: d.f168 / 100 || 0,
            pe: d.f162 / 100 || 0,
            totalValue: d.f116 / 100 || 0,
            flowValue: d.f117 / 100 || 0,
          });
        } else {
          console.warn('行情API返回异常，使用示例数据');
          resolve(mockData.getSampleQuote(code));
        }
      },
      fail(err) {
        console.warn('行情API请求失败，使用示例数据:', err.errMsg);
        resolve(mockData.getSampleQuote(code));
      }
    });
  });
}

/**
 * 搜索股票
 */
function searchStock(keyword) {
  return new Promise((resolve) => {
    wx.request({
      url: API.SEARCH,
      timeout: 5000,
      data: {
        input: keyword,
        type: 14,
        token: 'DEFAULT',
        count: 10
      },
      success(res) {
        if (res.data && res.data.QuotationCodeTable && res.data.QuotationCodeTable.Data) {
          const stocks = res.data.QuotationCodeTable.Data
            .filter(item => item.StockType === 'A' || item.StockType === 'ETF')
            .map(item => ({
              code: item.Code,
              name: item.Name,
              market: item.Market === 'SA' ? 'sh' : 'sz',
              type: item.StockType,
            }));
          resolve(stocks);
        } else {
          console.warn('搜索API返回异常，使用本地搜索');
          resolve(mockData.searchSampleStocks(keyword));
        }
      },
      fail(err) {
        console.warn('搜索API请求失败，使用本地搜索:', err.errMsg);
        resolve(mockData.searchSampleStocks(keyword));
      }
    });
  });
}

module.exports = {
  fetchKlineData,
  fetchQuote,
  searchStock,
  getSecid,
  getMarketCode,
  PERIOD_MAP,
};
