const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

exports.main = async (event) => {
  const { category, keyword, page = 1, pageSize = 20, sort = 'default' } = event;
  const skip = (page - 1) * pageSize;

  try {
    let query = db.collection('foods');

    if (category && category !== 'all') {
      query = query.where({ category });
    }

    // 关键词搜索
    if (keyword) {
      query = query.where({
        name: db.RegExp({ regexp: keyword, options: 'i' }),
      });
    }

    // 排序
    switch (sort) {
      case 'price-asc':
        query = query.orderBy('price', 'asc');
        break;
      case 'price-desc':
        query = query.orderBy('price', 'desc');
        break;
      case 'cal-asc':
        query = query.orderBy('calories', 'asc');
        break;
      case 'cal-desc':
        query = query.orderBy('calories', 'desc');
        break;
      default:
        query = query.orderBy('createdAt', 'desc');
    }

    const total = await query.count();
    const res = await query.skip(skip).limit(pageSize).get();

    return {
      success: true,
      data: res.data,
      total: total.total,
      page,
      pageSize,
      hasMore: skip + res.data.length < total.total,
    };
  } catch (err) {
    return { success: false, error: err.message };
  }
};
