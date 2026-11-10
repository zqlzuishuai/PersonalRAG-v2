<script setup>
/**
 * state/FailureBlock.vue —— 失败态
 * 整屏翻墨幕；中央 420×260 纯黑板 + 警示色双重描边标题（30px 字距 3，两侧实心竖条）；
 * 4 行 8–9.5px 日志以 240ms 间隔逐条打印，末行警示色并填实方块。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  reason: { type: String, default: '' },
  logs: {
    type: Array,
    default: () => ['AUTHORIZATION FAILED', 'CREDENTIAL NOT ON ISSUE BOOK', 'ATTEMPT COUNT DECREASED', 'RETURNING TO ACCESS PORTAL'],
  },
})

const shown = ref(1)
let timer = null

onMounted(() => {
  timer = setInterval(() => {
    shown.value += 1
    if (shown.value >= props.logs.length) {
      clearInterval(timer)
      timer = null
    }
  }, 240)
})

onBeforeUnmount(() => timer && clearInterval(timer))
</script>

<template>
  <div class="fb">
    <div class="fb__box">
      <div class="fb__head">
        <i class="fb__bar" />
        <span class="fb__title">WARNING</span>
        <i class="fb__bar" />
      </div>

      <ul class="fb__logs">
        <li
          v-for="(l, i) in props.logs"
          :key="l"
          class="fb__row"
          :class="{ 'is-visible': i < shown, 'is-last': i === props.logs.length - 1 }"
        >
          <span class="fb__text">{{ l }}</span>
          <i v-if="i >= 1 && i < shown" class="fb__sq" />
        </li>
      </ul>
    </div>

    <p class="fb__reason">{{ reason }}</p>

    <div class="fb__timer" aria-hidden="true">
      <i />
    </div>
  </div>
</template>

<style scoped>
.fb {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  pointer-events: none;
}

.fb__box {
  position: relative;
  width: 420px;
  height: 260px;
  padding: 26px 24px;
  background: #0b0b0c;
  border: 1px solid var(--alert);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* 第二重描边 */
.fb__box::before {
  content: '';
  position: absolute;
  inset: -5px;
  border: 1px solid var(--alert);
}

.fb__head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fb__bar {
  flex: none;
  width: 2px;
  height: 24px;
  background: var(--alert);
}

.fb__title {
  font-family: var(--font-sans);
  font-size: var(--t30);
  font-weight: 600;
  line-height: 1;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--alert);
}

.fb__logs {
  display: flex;
  flex-direction: column;
  gap: 9px;
  flex: 1;
}

.fb__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  opacity: 0;
}

.fb__row.is-visible {
  opacity: 1;
  animation: print-in var(--d-micro) linear both;
}

.fb__text {
  font-family: var(--font-mono);
  font-size: var(--t8);
  line-height: 1.6;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: #8b8882;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fb__row.is-last .fb__text {
  color: var(--alert);
}

.fb__sq {
  flex: none;
  width: 7px;
  height: 7px;
  background: var(--alert);
}

.fb__reason {
  font-family: var(--font-sans);
  font-size: var(--t125);
  letter-spacing: 1.4px;
  color: #f2f0eb;
  opacity: 0.82;
  text-align: center;
  max-width: 520px;
  line-height: 1.6;
}

.fb__timer {
  width: 168px;
  height: 2px;
  background: color-mix(in srgb, #ff7b00 26%, transparent);
}

.fb__timer i {
  display: block;
  height: 100%;
  background: var(--alert);
  animation: fb-count 2.6s linear forwards;
}

@keyframes fb-count {
  from {
    width: 100%;
  }
  to {
    width: 0%;
  }
}
</style>
