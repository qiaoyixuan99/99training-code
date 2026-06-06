const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  const { date, startDate, endDate } = event;

  try {
    if (date) {
      const res = await db.collection('diary')
        .where({ _openid: OPENID, date })
        .limit(1)
        .get();
      return {
        success: true,
        data: res.data.length > 0 ? res.data[0] : null,
      };
    }

    if (startDate && endDate) {
      const res = await db.collection('diary')
        .where({
          _openid: OPENID,
          date: db.command.gte(startDate).and(db.command.lte(endDate)),
        })
        .orderBy('date', 'asc')
        .get();
      return { success: true, data: res.data };
    }

    return { success: false, error: '请提供 date 或 startDate/endDate' };
  } catch (err) {
    return { success: false, error: err.message };
  }
};
