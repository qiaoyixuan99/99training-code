Component({
  properties: {
    food: {
      type: Object,
      value: {},
    },
    showCategory: {
      type: Boolean,
      value: false,
    },
  },

  data: {
    isLiked: false,
  },

  methods: {
    onTap() {
      this.triggerEvent('tap', { food: this.properties.food });
    },

    onLike(e) {
      e.stopPropagation();
      this.setData({ isLiked: !this.data.isLiked });
      this.triggerEvent('like', {
        food: this.properties.food,
        liked: !this.data.isLiked,
      });
    },

    onAddCart(e) {
      e.stopPropagation();
      this.triggerEvent('addcart', { food: this.properties.food });

      // 触发甜蜜动画
      this.triggerEvent('loveanim', {
        x: e.detail.x || 0,
        y: e.detail.y || 0,
      });
    },
  },
});
