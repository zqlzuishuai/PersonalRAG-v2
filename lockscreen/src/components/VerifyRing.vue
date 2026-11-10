<script setup>
/**
 * 中央断续验证环。
 * 关键逻辑：验证中细圆环反向旋转、卫星点转警示色、进度条随状态机推进；
 * 就绪时只保留静止断续环；授权与拒绝态分别淡出 / 保留作状态锚点。
 */
import { computed } from 'vue'
const props = defineProps({
  displayPhase: { type: String, required: true },
  progress: { type: Number, default: 0 },
})
const active = computed(() => props.displayPhase === 'verifying')
const idle = computed(() => props.displayPhase === 'idle')
</script>

<template>
  <div class="verify-wrap" :class="{ active, rejected: displayPhase === 'rejected', released: displayPhase === 'approved' || displayPhase === 'exiting' }">
    <svg class="ring-svg" viewBox="0 0 240 240" aria-hidden="true">
      <circle cx="120" cy="120" r="88" fill="none" :stroke="displayPhase === 'rejected' ? 'var(--warn)' : 'var(--line)'"
              stroke-width="1" stroke-dasharray="2 7" />
      <circle cx="120" cy="120" r="76" fill="none" :stroke="active ? 'var(--warn)' : 'var(--accent)'"
              stroke-width="2" stroke-dasharray="34 18 6 18" class="ring-rotor" />
      <circle cx="120" cy="120" r="64" fill="none" stroke="var(--line-soft)" stroke-width="1" />
      <circle cx="120" cy="32" r="5" :fill="active || displayPhase === 'rejected' ? 'var(--warn)' : 'var(--accent)'"
              class="satellite" />
    </svg>

    <div class="center-status mono micro">
      <template v-if="active">
        <div class="status-code">COMPARE {{ String(progress).padStart(3, '0') }}%</div>
        <div class="bar"><i :style="{ width: `${progress}%` }"></i></div>
      </template>
      <template v-else-if="idle">
        <!-- 待机：呼吸闪烁的按键提示；唤醒键只唤醒、不写入输入 -->
        <div class="idle-prompt">PRESS ANY KEY</div>
        <div class="idle-zh">按任意键唤醒</div>
      </template>
      <template v-else>
        <div class="status-code">STATE · {{ displayPhase.toUpperCase() }}</div>
        <div class="status-sub muted">ANCHOR / 04</div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.verify-wrap { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 240px; height: 240px; display: grid; place-items: center; transition: opacity 600ms ease; }
.verify-wrap.released { opacity: 0; }
.ring-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.ring-rotor { transform-origin: 120px 120px; }
.active .ring-rotor { animation: spin-reverse 2.4s linear infinite; stroke: var(--warn); }
.rejected .ring-rotor { animation: spin-reverse 6s linear infinite; }
.satellite { transform-origin: 120px 120px; }
.active .satellite { animation: spin-reverse 1.6s linear infinite, pulse 700ms ease-in-out infinite; }
.center-status { position: relative; text-align: center; z-index: 2; }
.status-code { font-size: 11px; letter-spacing: 0.18em; }
.status-sub { font-size: 9px; margin-top: 6px; }
.bar { width: 120px; height: 3px; margin: 10px auto 0; background: var(--line-soft); }
.bar i { display: block; height: 100%; background: var(--warn); transition: width 80ms linear; }
.idle-prompt { font-size: 13px; letter-spacing: 0.24em; animation: breathe 2.6s ease-in-out infinite; }
.idle-zh { font-size: 11px; margin-top: 8px; color: var(--muted); }
</style>
