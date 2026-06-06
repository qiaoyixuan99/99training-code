const cloud = require('wx-server-sdk');
cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV });
const db = cloud.database();

exports.main = async (event) => {
  const { OPENID } = cloud.getWXContext();
  const { items, totalPrice, totalCalories, note, date } = event;

  try {
    // 1. 创建订单记录
    await db.collection('orders').add({
      data: {
        _openid: OPENID,
        items,
        totalPrice,
        totalCalories,
        note: note || '',
        status: 'completed',
        createdAt: new Date(),
        date,
      },
    });

    // 2. 同步到饮食日记
    const diaryCol = db.collection('diary');
    const existing = await diaryCol.where({ _openid: OPENID, date }).get();

    // 判定餐次
    const hour = new Date().getHours();
    let mealType = 'snack';
    if (hour >= 6 && hour < 10) mealType = 'breakfast';
    else if (hour >= 10 && hour < 14) mealType = 'lunch';
    else if (hour >= 14 && hour < 17) mealType = 'snack';
    else if (hour >= 17 && hour < 21) mealType = 'dinner';

    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

    if (existing.data.length > 0) {
      const diary = existing.data[0];
      const meal = diary.meals[mealType];
      const newItems = items.map((item) => ({
        foodId: item.foodId,
        name: item.name,
        image: item.image,
        price: item.price,
        calories: item.calories,
        isDouble: item.isDouble,
        quantity: item.quantity,
        time,
      }));
      meal.items = [...meal.items, ...newItems];
      meal.totalCal += items.reduce(
        (sum, item) => sum + item.calories * (item.isDouble ? 2 : 1) * item.quantity, 0
      );
      await diaryCol.doc(diary._id).update({ data: { meals: diary.meals } });
    } else {
      const meals = {
        breakfast: { items: [], totalCal: 0 },
        lunch: { items: [], totalCal: 0 },
        dinner: { items: [], totalCal: 0 },
        snack: { items: [], totalCal: 0 },
      };
      meals[mealType].items = items.map((item) => ({
        foodId: item.foodId,
        name: item.name,
        image: item.image,
        price: item.price,
        calories: item.calories,
        isDouble: item.isDouble,
        quantity: item.quantity,
        time,
      }));
      meals[mealType].totalCal = items.reduce(
        (sum, item) => sum + item.calories * (item.isDouble ? 2 : 1) * item.quantity, 0
      );
      await diaryCol.add({
        data: { _openid: OPENID, date, meals },
      });
    }

    // 3. 清空购物车
    await db.collection('carts').where({ _openid: OPENID }).remove();

    return { success: true, mealType };
  } catch (err) {
    return { success: false, error: err.message };
  }
};
