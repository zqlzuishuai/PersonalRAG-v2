<script setup>
/**
 * 中央三维 ∞ 形鳍片雕塑（纯 CSS 3D，不引入任何三维库）。
 * 关键逻辑：
 * - 常驻缓慢旋转；验证中加速、对齐并向镜头推近（外层 scale，内层旋转，互不冲突）。
 * - 拒绝态转石墨与警示色并叠加扰动；待机时由全局 is-idle 降频。
 * - 无三维能力 / 降级视图时退化为同色系纸面与朴素 ∞ 线稿，状态语义不变。
 */
import { computed } from 'vue'
const props = defineProps({
  displayPhase: { type: String, required: true },
  threeD: { type: Boolean, default: true },
  fallback: { type: Boolean, default: false },
})
// 关键逻辑：鳍片沿 ∞ 参数曲线（Gerono 双纽线）分布，并按切线方向旋转，
// 形成连续的三维 ∞ 形鳍片带，而不是放射状风车。
const blades = computed(() => Array.from({ length: 20 }, (_, i) => {
  const t = (i / 20) * Math.PI * 2
  const x = 150 * Math.sin(t)
  const y = 62 * Math.sin(2 * t)
  const dx = 150 * Math.cos(t)
  const dy = 124 * Math.cos(2 * t)
  const angle = (Math.atan2(dy, dx) * 180) / Math.PI
  return {
    x: `${x.toFixed(1)}px`,
    y: `${y.toFixed(1)}px`,
    a: `${angle.toFixed(1)}deg`,
    ry: `${((i * 17) % 80) - 40}deg`,
  }
}))
const mode = computed(() => {
  const p = props.displayPhase
  if (p === 'rejected') return 'mode-rejected'
  if (p === 'verifying') return 'mode-verifying'
  if (p === 'approved' || p === 'exiting') return 'mode-released'
  return 'mode-idle-run'
})
const flat = computed(() => !props.threeD || props.fallback)
</script>

<template>
  <div class="sculpture-wrap" :class="[mode, { flat }]" aria-hidden="true">
    <!-- ∞ 底稿：两种模式下都存在，保证降级视图语义一致 -->
    <svg class="infinity-base" viewBox="0 0 400 220">
      <path d="M200 110 C160 46 58 46 58 110 C58 174 160 174 200 110" fill="none" stroke="var(--line)" stroke-width="1.4" />
      <path d="M200 110 C240 46 342 46 342 110 C342 174 240 174 200 110" fill="none" stroke="var(--line)" stroke-width="1.4" />
      <circle cx="200" cy="110" r="4" fill="var(--accent)" />
    </svg>

    <div v-if="!flat" class="sculpture-shell">
      <div class="sculpture">
        <div
          v-for="(blade, i) in blades"
          :key="i"
          class="sculpture-blade"
          :style="{ '--x': blade.x, '--y': blade.y, '--a': blade.a, '--ry': blade.ry }"
        ></div>
      </div>
    </div>

    <div v-else class="flat-paper">
      <span class="flat-mark display">∞</span>
      <span class="flat-note mono micro muted">3D DISABLED · PAPER FALLBACK</span>
    </div>
  </div>
</template>

<style scoped>
.sculpture-wrap { position: absolute; inset: 0; display: grid; place-items: center; }
.infinity-base { position: absolute; width: 78%; max-width: 560px; opacity: 0.75; }
.sculpture-shell {
  position: absolute; width: 420px; height: 260px;
  transform-style: preserve-3d;
  transition: transform 1200ms cubic-bezier(0.16, 1, 0.3, 1);
}
.sculpture {
  position: absolute; inset: 0;
  transform-style: preserve-3d;
  animation: slow-turn 22s linear infinite;
}
@keyframes slow-turn {
  from { transform: rotateY(0deg) rotateX(9deg); }
  to { transform: rotateY(360deg) rotateX(9deg); }
}
.sculpture-blade {
  position: absolute; left: 50%; top: 50%;
  width: 74px; height: 16px; margin: -8px 0 0 -37px;
  background: var(--ink);
  border-left: 2px solid var(--accent);
  box-shadow: var(--ao);
  transform: translate(var(--x), var(--y)) rotate(var(--a)) rotateY(var(--ry));
  opacity: 0.86;
}
.sculpture-blade:nth-child(even) { background: var(--card); border-left-color: var(--ink); opacity: 0.7; }

/* 验证中：加速对齐 + 向镜头推近 */
.mode-verifying .sculpture { animation-duration: 2.6s; }
.mode-verifying .sculpture-shell { transform: scale(1.22) translateZ(80px); }
.mode-verifying .sculpture-blade { border-left-color: var(--warn); }
/* 拒绝态：石墨 + 警示色 + 扰动 */
.mode-rejected .sculpture-blade { background: #43464b; border-left-color: var(--warn); }
.mode-rejected .sculpture-blade:nth-child(even) { background: #2b2d31; }
.mode-rejected .sculpture-shell { transform: scale(1.06) rotate(1.5deg); animation: glitch 700ms steps(2, end) 1; }
/* 授权：雕塑淡出，让位给恢复的桌面画面 */
.mode-released .sculpture-shell { opacity: 0; transform: scale(1.5); }

.flat-paper { position: relative; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.flat-mark { font-size: 130px; line-height: 1; color: var(--ink); opacity: 0.16; }
.flat-note { font-size: 10px; }
.sculpture-wrap.flat .infinity-base { opacity: 0.3; }
</style>
