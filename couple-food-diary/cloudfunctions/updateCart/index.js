const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  const { foodId, isDouble, quantity } = event;

  try {
    const cartCol = db.collection('carts');
    const existing = await cartCol
      .where({ _openid: OPENID, foodId, isDouble: isDouble || false })
      .get();

    if (existing.data.length === 0) {
      return { success: false, error: '购物车项不存在' };
    }

    if (quantity <= 0) {
      await cartCol.doc(existing.data[0]._id).remove();
    } else {
      await cartCol.doc(existing.data[0]._id).update({ data: { quantity } });
    }

    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
};
