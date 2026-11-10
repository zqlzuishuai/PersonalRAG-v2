<script setup>
/**
 * state/VerifyComplex.vue —— 主带中央的「准星 / 进度」复合体
 * 常态：一枚细描圆环 + 四道刻度 + 状态字。
 * 进行中：3 组断续细弧以 9s / 3.8s / 2.6s 反向匀速自转，下方 168×9 双线框进度条。
 */
import { computed } from 'vue'

const props = defineProps({
  running: { type: Boolean, default: false },
  pct: { type: Number, default: 0 },
  word: { type: String, default: 'SEALED' },
  zh: { type: String, default: '等待凭据' },
})

const width = computed(() => `${Math.max(0, Math.min(100, props.pct)).toFixed(1)}%`)
</script>

<template>
  <div class="vc" :class="{ 'is-running': running }">
    <div class="vc__ring">
      <svg class="vc__svg" viewBox="0 0 200 200" aria-hidden="true">
        <circle class="vc__base" cx="100" cy="100" r="92" />
        <g class="vc__ticks">
          <line x1="100" y1="2" x2="100" y2="16" />
          <line x1="198" y1="100" x2="184" y2="100" />
          <line x1="100" y1="198" x2="100" y2="184" />
          <line x1="2" y1="100" x2="16" y2="100" />
        </g>
        <circle class="vc__arc vc__arc--a" cx="100" cy="100" r="92" />
        <circle class="vc__arc vc__arc--b" cx="100" cy="100" r="76" />
        <circle class="vc__arc vc__arc--c" cx="100" cy="100" r="60" />
      </svg>

      <div class="vc__core">
        <span class="vc__word">{{ running ? 'VERIFYING' : word }}</span>
        <span class="vc__zh">{{ running ? '正在比对授权口令' : zh }}</span>
      </div>

      <i class="vc__pip vc__pip--1" />
      <i class="vc__pip vc__pip--2" />
    </div>

    <div class="vc__prog" :class="{ 'is-on': running }">
      <span class="lbl">PROCESSING</span>
      <div class="pb">
        <div class="pb__track">
          <div class="pb__fill" :style="{ width }" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vc {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}

.vc__ring {
  position: relative;
  width: 220px;
  height: 220px;
  flex: none;
}

.vc__svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.vc__base {
  fill: none;
  stroke: var(--hair);
  stroke-width: 1.4;
}

.vc__ticks line {
  stroke: var(--hair);
  stroke-width: 2;
}

.vc__arc {
  fill: none;
  stroke: var(--fg);
  stroke-width: 1.4;
  transform-origin: 100px 100px;
  opacity: 0;
}

.vc__arc--a {
  stroke-dasharray: 96 24 40 22 60 20;
}

.vc__arc--b {
  stroke-dasharray: 30 26 12 18;
  stroke-width: 2;
}

.vc__arc--c {
  stroke-dasharray: 8 14;
  stroke: var(--accent);
  stroke-width: 2;
}

.is-running .vc__arc {
  opacity: 1;
}

.is-running .vc__arc--a {
  animation: spin 9s linear infinite;
}

.is-running .vc__arc--b {
  animation: spin-rev 3.8s linear infinite;
}

.is-running .vc__arc--c {
  animation: spin 2.6s linear infinite;
}

.vc__core {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  text-align: center;
}

.vc__word {
  font-family: var(--font-mono);
  font-size: var(--t95);
  letter-spacing: 2.4px;
  text-transform: uppercase;
  color: var(--fg);
}

.vc__zh {
  font-family: var(--font-sans);
  font-size: var(--t11);
  letter-spacing: 2px;
  color: var(--dim);
}

.vc__pip {
  position: absolute;
  width: 5px;
  height: 5px;
  background: var(--accent);
  opacity: 0;
}

.is-running .vc__pip {
  opacity: 1;
}

.vc__pip--1 {
  top: 26px;
  left: 26px;
}

.vc__pip--2 {
  right: 30px;
  bottom: 34px;
  width: 3px;
  height: 3px;
  background: var(--fg);
}

/* 168×9 双线框进度条，内嵌 2px 填充 */
.vc__prog {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  opacity: 0;
  transition: opacity var(--d-micro) linear;
}

.vc__prog.is-on {
  opacity: 1;
}

.pb {
  width: 168px;
  height: 9px;
  border: 1px solid var(--hair);
  padding: 1px;
}

.pb__track {
  position: relative;
  width: 100%;
  height: 100%;
  border: 1px solid var(--hair-soft);
}

.pb__fill {
  position: absolute;
  left: 0;
  top: 50%;
  height: 2px;
  transform: translateY(-50%);
  background: var(--accent);
  transition: width 1.6s linear;
}
</style>
