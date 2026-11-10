<script setup>
/**
 * 封存卡片：当前桌面画面被封存为标本，带四角取景框、荧光扫描线与归档说明。
 * 关键逻辑：入场时沿弧线缩小落入左栏（data-motion="sealing"）；
 * 授权出场时同一动画反向播放（animation-direction: reverse），保证互为镜像。
 * 缩写码中嵌入 ∞ 符号，状态标签随状态切换。
 */
import { computed } from 'vue'
import { COPY, IDENTITY, field } from '../config'
const props = defineProps({
  displayPhase: { type: String, required: true },
  lockedAt: { type: String, required: true },
  sealing: { type: Boolean, default: false },
  releasing: { type: Boolean, default: false },
})
const motion = computed(() => props.sealing ? 'sealing' : props.releasing ? 'releasing' : 'static')
const statusLabel = computed(() => {
  switch (props.displayPhase) {
    case 'entering': return 'SEALING'
    case 'verifying': return 'SCANNING'
    case 'rejected': return 'RETAINED'
    case 'approved': case 'exiting': return 'RELEASING'
    default: return 'SEALED'
  }
})
</script>

<template>
  <div class="specimen stage-card" :data-motion="motion">
    <span class="corner tl"></span><span class="corner tr"></span>
    <span class="corner bl"></span><span class="corner br"></span>
    <span class="scanline"></span>

    <div class="spec-head mono micro">
      <span>{{ COPY.specimen }}</span><span>∞ / 01</span>
    </div>

    <div class="spec-frame frame-corners">
      <!-- 桌面画面缩略：与入场/出场遮罩中的满屏桌面同源，保证首尾帧一致 -->
      <div class="desktop-frame">
        <div class="df-bar"><i></i><i></i><i></i></div>
        <div class="df-body">
          <div class="df-side"></div>
          <div class="df-main">
            <div class="df-chart"></div>
            <div class="df-lines"><i></i><i></i><i></i><i></i></div>
          </div>
        </div>
      </div>
      <div class="smoke"></div>
      <span class="spec-code display">S∞·4417</span>
      <span class="spec-stamp mono">{{ statusLabel }}</span>
    </div>

    <div class="spec-foot mono micro">
      <span class="ellipsis">{{ field(IDENTITY.host) }}</span>
      <span>{{ lockedAt }}</span>
    </div>
    <p class="spec-note mono micro muted ellipsis">
      FRAME CAPTURED · ARCHIVED / 画面已封存归档
    </p>
  </div>
</template>

<style scoped>
.specimen {
  position: relative;
  height: 100%;
  padding: 14px 16px;
  background: var(--ink);
  color: var(--paper);
  box-shadow: var(--shadow);
  overflow: hidden;
  transform-origin: center center;
}
/* 入场落卡 / 出场放大：同一组关键帧，反向即为镜像 */
.specimen[data-motion="sealing"] { animation: seal-in 1500ms cubic-bezier(0.16, 1, 0.3, 1) both; }
.specimen[data-motion="releasing"] { animation: seal-in 1500ms cubic-bezier(0.16, 1, 0.3, 1) reverse both; }
@keyframes seal-in {
  0% { transform: scale(4.55) translate(9%, -6%) rotate(-1.2deg); opacity: 0.55; }
  55% { transform: scale(1.35) translate(2%, -1%) rotate(0.4deg); opacity: 1; }
  100% { transform: none; opacity: 1; }
}
.specimen :deep(.corner) { border-color: var(--accent); }
.spec-head, .spec-foot { display: flex; justify-content: space-between; gap: 10px; color: var(--paper); opacity: 0.72; }
.spec-frame {
  position: relative;
  height: 62%;
  margin: 12px 0 10px;
  overflow: hidden;
  border: 1px solid rgba(231, 229, 225, 0.18);
}
.desktop-frame { position: absolute; inset: 0; filter: grayscale(1) contrast(1.15) brightness(0.7); }
.smoke {
  position: absolute; inset: 0;
  background:
    radial-gradient(60% 80% at 25% 70%, rgba(231, 229, 225, 0.14), transparent 70%),
    radial-gradient(50% 60% at 75% 30%, rgba(231, 229, 225, 0.1), transparent 72%);
  mix-blend-mode: screen;
}
.spec-code {
  position: absolute; left: 12px; bottom: 8px;
  font-size: 34px; color: var(--paper); letter-spacing: 0.02em;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.7);
}
.spec-stamp {
  position: absolute; right: 8px; top: 8px;
  font-size: 10px; letter-spacing: 0.16em;
  padding: 3px 6px; color: #111214; background: var(--accent);
}
.spec-note { margin: 8px 0 0; opacity: 0.6; }
.app-shell[data-tone="reject"] .specimen { background: #050505; }
</style>
