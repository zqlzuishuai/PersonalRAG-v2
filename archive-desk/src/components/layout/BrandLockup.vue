<script setup>
/**
 * layout/BrandLockup.vue —— 品牌带的三行锁排
 * 第一行大字；第二行用字距拉伸至等宽；第三行同样拉伸至等宽。
 * 三行共左列线、共右边界，构成一个矩形。
 */
import { org } from '@/data/registry'
</script>

<template>
  <div class="brand">
    <div class="brand__l1">{{ org.en }}</div>
    <div class="brand__l2">{{ org.en2 }}</div>
    <div class="brand__l3">{{ org.en3 }}</div>
    <div class="brand__meta">
      <span class="mono">{{ org.code }}</span>
      <span class="brand__sep" />
      <span>{{ org.desk }}</span>
    </div>
  </div>
</template>

<style scoped>
.brand {
  width: max-content;
  max-width: 46%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  user-select: none;
}

.brand__l1 {
  font-family: var(--font-sans);
  font-size: var(--t21);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.4px;
  text-transform: uppercase;
  color: var(--fg);
}

.brand__l2,
.brand__l3 {
  font-family: var(--font-sans);
  font-size: var(--t11);
  font-weight: 500;
  line-height: 1;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--fg);
  text-align: justify;
  text-align-last: justify;
  -moz-text-align-last: justify;
}

.brand__l3 {
  color: var(--dim);
}

.brand__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-family: var(--font-mono);
  font-size: var(--t8);
  line-height: 1.1;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--dim);
  white-space: nowrap;
}

.brand__sep {
  width: 18px;
  height: 1px;
  background: var(--line);
}

.mode-column .brand {
  max-width: 100%;
}
</style>
