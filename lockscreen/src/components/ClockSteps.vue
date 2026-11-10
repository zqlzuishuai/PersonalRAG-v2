<script setup>
/**
 * 大号走秒时钟 + 步骤点。
 * 关键逻辑：activeStep 由状态机派生，验证中前移到 VERIFY，授权后到 RELEASE；
 * 时钟每秒由 useLockMachine 的 ticker 驱动，与字幕、日志同步。
 */
import { COPY } from '../config'
defineProps({
  clock: { type: String, required: true },
  elapsed: { type: String, required: true },
  lockedAt: { type: String, required: true },
  activeStep: { type: Number, required: true },
  stepLabels: { type: Array, required: true },
  displayPhase: { type: String, default: 'ready' },
})
</script>

<template>
  <div class="clock-block">
    <div class="clock-head mono micro muted">
      <span>LOCAL / 本地时刻</span><span>{{ COPY.classified }}</span>
    </div>
    <div class="clock display tabular">{{ clock }}<span class="cursor" aria-hidden="true">_</span></div>
    <div class="clock-meta mono micro">
      <span>LOCK {{ lockedAt }}</span>
      <span>DUR {{ elapsed }}</span>
    </div>
    <ol class="steps" aria-label="流程步骤">
      <li
        v-for="(label, i) in stepLabels"
        :key="label"
        :class="{ done: i < activeStep, current: i === activeStep }"
      >
        <i class="dot" aria-hidden="true"></i>
        <span class="mono">{{ String(i + 1).padStart(2, '0') }} {{ label }}</span>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.clock-block { text-align: right; }
.clock-head { display: flex; justify-content: space-between; gap: 12px; }
.clock {
  font-size: 88px;
  line-height: 1;
  margin-top: 6px;
  letter-spacing: -0.05em;
}
.cursor { font-size: 46px; color: var(--accent); animation: blink 1s steps(1) infinite; }
.clock-meta { display: flex; justify-content: flex-end; gap: 22px; margin-top: 8px; color: var(--muted); }
.steps { list-style: none; display: flex; justify-content: flex-end; gap: 16px; margin: 22px 0 0; padding: 0; }
.steps li { display: flex; align-items: center; gap: 7px; font-size: 11px; color: var(--muted); }
.dot { width: 8px; height: 8px; border: 1px solid var(--line); background: transparent; }
.steps li.done .dot { background: var(--ink); border-color: var(--ink); }
.steps li.current { color: var(--ink); }
.steps li.current .dot { background: var(--accent); border-color: var(--accent); animation: pulse 1.4s ease-in-out infinite; }
@media (max-width: 520px) {
  .clock { font-size: 54px; }
  .steps { justify-content: flex-start; flex-wrap: wrap; }
  .clock-block { text-align: left; }
  .clock-head, .clock-meta { justify-content: flex-start; }
}
</style>
