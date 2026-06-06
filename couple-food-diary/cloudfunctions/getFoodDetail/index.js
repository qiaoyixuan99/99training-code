const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

exports.main = async (event) => {
  const { id } = event;
  try {
    const res = await db.collection('foods').doc(id).get();
    return { success: true, data: res.data };
  } catch (err) {
    return { success: false, error: err.message };
  }
};
