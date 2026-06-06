const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

exports.main = async (event) => {
  const { food } = event;

  try {
    const res = await db.collection('foods').add({
      data: {
        ...food,
        createdAt: new Date(),
        updatedAt: new Date(),
      },
    });
    return { success: true, id: res._id };
  } catch (err) {
    return { success: false, error: err.message };
  }
};
