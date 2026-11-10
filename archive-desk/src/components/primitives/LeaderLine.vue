<script setup>
/**
 * primitives/LeaderLine.vue —— 跨轴连接只允许 1.2px 引线 + 小标签
 * 引线端点为一枚 3.5px 实心圆。
 */
defineProps({
  dir: { type: String, default: 'h' }, // h | v
  len: { type: Number, default: 48 },
  label: { type: String, default: '' },
})
</script>

<template>
  <div class="ll" :class="`ll--${dir}`" :style="{ '--len': `${len}px` }">
    <span v-if="label" class="ll__label">{{ label }}</span>
    <span class="ll__line" />
    <span class="ll__dot" />
  </div>
</template>

<style scoped>
.ll {
  display: flex;
  align-items: center;
  gap: 6px;
  pointer-events: none;
}

.ll--v {
  flex-direction: column;
}

.ll__label {
  font-family: var(--font-mono);
  font-size: var(--t8);
  line-height: 1.1;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--dim);
  white-space: nowrap;
}

.ll__line {
  display: block;
  background: var(--hair);
}

.ll--h .ll__line {
  width: var(--len);
  height: 1.2px;
}

.ll--v .ll__line {
  width: 1.2px;
  height: var(--len);
}

.ll__dot {
  display: block;
  flex: none;
  width: 3.5px;
  height: 3.5px;
  border-radius: 50%;
  background: var(--fg);
}
</style>
