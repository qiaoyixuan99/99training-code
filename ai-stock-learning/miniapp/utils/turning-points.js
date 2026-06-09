// 拐点检测算法
// 基于局部极值 + 趋势变化 + 波动率分析

/**
 * 检测K线拐点
 * @param {Array} klines - K线数据数组
 * @param {Object} options - 配置项
 * @returns {Array} 拐点列表
 */
function detectTurningPoints(klines, options = {}) {
  const {
    lookback = 5,           // 回看窗口（左右各N根K线）
    minAmplitude = 1.5,     // 最小波动幅度（%），过滤噪音
    minDistance = 8,        // 相邻拐点最小间距（根K线）
    useClose = true,        // 是否用收盘价判断（false则用最高/最低）
  } = options;

  if (klines.length < lookback * 2 + 1) {
    return [];
  }

  const points = [];
  const n = klines.length;

  // 第一步：找局部极值
  for (let i = lookback; i < n - lookback; i++) {
    const leftSlice = klines.slice(i - lookback, i);
    const rightSlice = klines.slice(i + 1, i + lookback + 1);
    const current = klines[i];

    const priceCheck = useClose ? 'close' : 'high';
    const priceCheckLow = useClose ? 'close' : 'low';

    // 检测顶部拐点（局部最高点）
    const isPeak = leftSlice.every(k => k[priceCheck] <= current[priceCheck])
      && rightSlice.every(k => k[priceCheck] <= current[priceCheck])
      && leftSlice.some(k => k[priceCheck] < current[priceCheck]);

    // 检测底部拐点（局部最低点）
    const isValley = leftSlice.every(k => k[priceCheckLow] >= current[priceCheckLow])
      && rightSlice.every(k => k[priceCheckLow] >= current[priceCheckLow])
      && leftSlice.some(k => k[priceCheckLow] > current[priceCheckLow]);

    if (isPeak || isValley) {
      points.push({
        index: i,
        time: current.time,
        price: isPeak ? current.high : current.low,
        closePrice: current.close,
        type: isPeak ? 'peak' : 'valley',   // peak=顶部 valley=底部
        volume: current.volume,
        changePct: current.changePct,
      });
    }
  }

  // 第二步：过滤噪音 —— 合并距离太近的同向拐点，保留极端值
  const merged = mergeNearbyPoints(points, minDistance);

  // 第三步：标记拐点强度
  const enriched = merged.map((point, i) => {
    const strength = calculateStrength(point, klines, i, merged);
    const label = classifyPoint(point, strength, klines);
    return {
      ...point,
      strength,       // 1-10 强度评分
      label,          // 拐点分类标签
    };
  });

  // 第四步：添加拐点间的趋势信息
  const withTrends = addTrendInfo(enriched, klines);

  return withTrends;
}

/**
 * 合并近距离同向拐点
 */
function mergeNearbyPoints(points, minDistance) {
  if (points.length <= 1) return points;

  const merged = [];
  let i = 0;

  while (i < points.length) {
    let group = [points[i]];
    let j = i + 1;

    // 收集附近同向的拐点
    while (j < points.length
      && points[j].index - points[i].index < minDistance
      && points[j].type === points[i].type) {
      group.push(points[j]);
      j++;
    }

    // 保留该组中最极端的拐点
    if (group.length === 1) {
      merged.push(group[0]);
    } else {
      const best = points[i].type === 'peak'
        ? group.reduce((a, b) => a.price >= b.price ? a : b)
        : group.reduce((a, b) => a.price <= b.price ? a : b);
      merged.push(best);
    }

    i = j;
  }

  return merged;
}

/**
 * 计算拐点强度 (1-10)
 */
function calculateStrength(point, klines, pointIdx, allPoints) {
  let score = 5;

  const current = klines[point.index];

  // 1. 振幅贡献（振幅越大越重要）
  if (current.amplitude > 5) score += 2;
  else if (current.amplitude > 3) score += 1;
  else if (current.amplitude < 1) score -= 1;

  // 2. 成交量确认（放量拐点更可靠）
  const avgVol = klines.slice(Math.max(0, point.index - 20), point.index)
    .reduce((s, k) => s + k.volume, 0) / 20;
  if (current.volume > avgVol * 2) score += 2;
  else if (current.volume > avgVol * 1.5) score += 1;
  else if (current.volume < avgVol * 0.5) score -= 1;

  // 3. 拐点间的价格差（与前一个拐点的涨跌幅）
  if (pointIdx > 0) {
    const prev = allPoints[pointIdx - 1];
    const pctChange = Math.abs((point.price - prev.price) / prev.price * 100);
    if (pctChange > 10) score += 2;
    else if (pctChange > 5) score += 1;
  }

  // 4. 长影线加分（反转信号）
  const upperShadow = current.high - Math.max(current.open, current.close);
  const lowerShadow = Math.min(current.open, current.close) - current.low;
  const body = Math.abs(current.open - current.close);
  if (body > 0) {
    const shadowRatio = point.type === 'peak'
      ? upperShadow / body
      : lowerShadow / body;
    if (shadowRatio > 2) score += 1;
  }

  return Math.max(1, Math.min(10, Math.round(score)));
}

/**
 * 分类拐点
 */
function classifyPoint(point, strength, klines) {
  const current = klines[point.index];

  if (point.type === 'peak') {
    // 判断是主要顶部还是次要回调顶
    if (strength >= 7) return '🔴 主要顶部';
    if (strength >= 5) return '🟠 阶段高点';
    return '🟡 短顶';
  } else {
    if (strength >= 7) return '🟢 主要底部';
    if (strength >= 5) return '🔵 阶段低点';
    return '🟣 短底';
  }
}

/**
 * 添加拐点间的趋势信息
 */
function addTrendInfo(points, klines) {
  return points.map((point, i) => {
    if (i === 0) {
      return { ...point, trendBefore: 'start', trendDays: 0, changeFromPrev: 0 };
    }

    const prev = points[i - 1];
    const changePct = ((point.price - prev.price) / prev.price * 100).toFixed(2);
    const days = point.index - prev.index;

    let trendBefore;
    if (point.type === 'peak') {
      trendBefore = '上涨';  // 峰前必涨
    } else {
      trendBefore = '下跌';  // 谷前必跌
    }

    // 更细致的趋势判断
    if (Math.abs(parseFloat(changePct)) < 1) {
      trendBefore = '横盘';
    }

    return {
      ...point,
      trendBefore,
      trendDays: days,
      changeFromPrev: parseFloat(changePct),
    };
  });
}

/**
 * 获取AI分析用的拐点上下文
 * 返回：当前拐点 + 前后各2个拐点 + K线特征数据
 */
function getAnalysisContext(turningPoints, targetIndex, klines) {
  const point = turningPoints[targetIndex];
  if (!point) return null;

  const contextKlines = klines.slice(
    Math.max(0, point.index - 15),
    Math.min(klines.length, point.index + 16)
  );

  const nearbyPoints = turningPoints.filter((p, i) =>
    Math.abs(i - targetIndex) <= 2 && i !== targetIndex
  );

  return {
    point,
    nearbyPoints,
    contextKlines,
    totalKlines: klines.length,
    latestPrice: klines[klines.length - 1]?.close || 0,
  };
}

/**
 * 寻找关键支撑/压力位（基于历史拐点聚合）
 */
function findKeyLevels(turningPoints, klines) {
  const levels = {
    support: [],    // 支撑位
    resistance: [], // 压力位
  };

  if (turningPoints.length < 3) return levels;

  // 从底部拐点聚类找支撑位
  const valleys = turningPoints.filter(p => p.type === 'valley');
  const peaks = turningPoints.filter(p => p.type === 'peak');

  // 简单的价格区间聚类
  levels.support = clusterPrices(valleys.map(p => p.price), 0.02);
  levels.resistance = clusterPrices(peaks.map(p => p.price), 0.02);

  // 当前价附近的关键位
  const latestPrice = klines[klines.length - 1]?.close || 0;
  levels.nearestSupport = findNearestLevel(levels.support, latestPrice, 'below');
  levels.nearestResistance = findNearestLevel(levels.resistance, latestPrice, 'above');

  return levels;
}

function clusterPrices(prices, tolerance) {
  if (prices.length === 0) return [];
  const sorted = [...prices].sort((a, b) => a - b);
  const clusters = [];
  let current = [sorted[0]];

  for (let i = 1; i < sorted.length; i++) {
    const avg = current.reduce((s, p) => s + p, 0) / current.length;
    if (Math.abs(sorted[i] - avg) / avg < tolerance) {
      current.push(sorted[i]);
    } else {
      clusters.push(current.reduce((s, p) => s + p, 0) / current.length);
      current = [sorted[i]];
    }
  }
  clusters.push(current.reduce((s, p) => s + p, 0) / current.length);
  return clusters.map(c => Math.round(c * 100) / 100);
}

function findNearestLevel(levels, price, direction) {
  if (direction === 'below') {
    const below = levels.filter(l => l < price);
    return below.length > 0 ? Math.max(...below) : null;
  } else {
    const above = levels.filter(l => l > price);
    return above.length > 0 ? Math.min(...above) : null;
  }
}

module.exports = {
  detectTurningPoints,
  getAnalysisContext,
  findKeyLevels,
};
