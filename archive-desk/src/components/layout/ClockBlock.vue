<script setup>
/** layout/ClockBlock.vue —— 品牌带右端：时:分 + 秒位、日期、终端行 */
import { onBeforeUnmount, ref } from 'vue'
import { fullDate, hm } from '@/utils/format'
import { org } from '@/data/registry'

const now = ref(new Date())
const tick = setInterval(() => {
  now.value = new Date()
}, 1000)
onBeforeUnmount(() => clearInterval(tick))

const secs = () => String(now.value.getSeconds()).padStart(2, '0')
</script>

<template>
  <div class="clock">
    <div class="clock__time">
      <span class="mono">{{ hm(now) }}</span>
      <span class="mono clock__sec">{{ secs() }}</span>
    </div>
    <div class="clock__date lbl">{{ fullDate(now) }}</div>
    <div class="clock__term lbl">
      <i class="clock__mark" />
      <span>{{ org.mark }}</span>
      <span>TERMINAL · {{ org.code }}</span>
    </div>
  </div>
</template>

<style scoped>
.clock {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  user-select: none;
}

.clock__time {
  position: relative;
  display: flex;
  align-items: flex-start;
  font-size: var(--t46);
  line-height: 0.9;
  letter-spacing: -1.5px;
  color: var(--fg);
  font-variant-numeric: tabular-nums;
}

.clock__sec {
  font-size: var(--t11);
  line-height: 1;
  letter-spacing: 0.5px;
  color: var(--dim);
  transform: translateY(2px);
  margin-left: 2px;
}

.clock__date {
  color: var(--fg);
}

.clock__term {
  display: flex;
  align-items: center;
  gap: 6px;
}

.clock__mark {
  width: 5px;
  height: 5px;
  background: var(--fg);
}

.clock__term span:first-of-type {
  font-size: var(--t95);
  letter-spacing: 0;
}

.mode-column .clock__time {
  font-size: var(--t30);
}
</style>
