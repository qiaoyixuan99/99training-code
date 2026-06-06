const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  const { foodId, name, image, price, calories, isDouble, quantity, category } = event;

  try {
    const cartCol = db.collection('carts');
    const existing = await cartCol
      .where({ _openid: OPENID, foodId, isDouble: isDouble || false })
      .get();

    if (existing.data.length > 0) {
      await cartCol.doc(existing.data[0]._id).update({
        data: { quantity: existing.data[0].quantity + (quantity || 1) },
      });
    } else {
      await cartCol.add({
        data: {
          _openid: OPENID,
          foodId,
          name,
          image,
          price,
          calories,
          isDouble: isDouble || false,
          quantity: quantity || 1,
          category,
          createdAt: new Date(),
        },
      });
    }

    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
};
