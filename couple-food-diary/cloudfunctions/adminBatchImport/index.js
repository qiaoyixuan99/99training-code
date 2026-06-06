const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

exports.main = async (event) => {
  const { foods } = event;

  if (!Array.isArray(foods) || foods.length === 0) {
    return { success: false, error: '数据格式错误，需要非空数组' };
  }

  try {
    const col = db.collection('foods');
    const now = new Date();
    let count = 0;

    // 批量写入（云开发单次最多20条）
    const batchSize = 20;
    for (let i = 0; i < foods.length; i += batchSize) {
      const batch = foods.slice(i, i + batchSize).map((food) => ({
        ...food,
        createdAt: now,
        updatedAt: now,
      }));

      const promises = batch.map((food) => col.add({ data: food }));
      await Promise.all(promises);
      count += batch.length;
    }

    return { success: true, count };
  } catch (err) {
    return { success: false, error: err.message };
  }
};
