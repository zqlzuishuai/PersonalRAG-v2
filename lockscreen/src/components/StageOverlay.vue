<script setup>
/**
 * 入场 / 出场遮罩、桌面画面与欢迎横幅。
 * 关键逻辑：
 * - 入场首帧是满屏桌面画面，随后沿弧线缩小为标本卡片并淡出；
 * - 出场用同一关键帧 animation-direction: reverse，末帧回到同一桌面画面，
 *   因此首尾帧与桌面画面一致、过渡互为镜像；
 * - 无桌面画面时改为居中标志 + 欢迎横幅（不新增其它模块）。
 */
import { computed } from 'vue'
import { WORDMARK, COPY } from '../config'
const props = defineProps({
  displayPhase: { type: String, required: true },
  releaseDone: { type: Boolean, default: false },
  hasDesktopFrame: { type: Boolean, default: true },
})
const emit = defineEmits(['relock'])
const frameMode = computed(() => {
  if (props.displayPhase === 'entering') return 'sealing'
  if (props.displayPhase === 'approved' || props.displayPhase === 'exiting') return 'releasing'
  return 'hidden'
})
const showBanner = computed(() => props.releaseDone && props.displayPhase === 'exiting')
</script>

<template>
  <div class="overlay" :class="{ 'banner-on': showBanner }">
    <!-- 桌面画面：与封存卡片使用同一 .desktop-frame 结构 -->
    <div v-if="hasDesktopFrame" class="overlay-frame compact-hide" :data-mode="frameMode" aria-hidden="true">
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
      <span class="corner tl"></span><span class="corner tr"></span>
      <span class="corner bl"></span><span class="corner br"></span>
      <span class="scanline"></span>
      <div class="frame-caption mono micro">{{ displayPhase === 'entering' ? 'FRAME CAPTURE / 画面封存中' : 'FRAME RESTORE / 画面恢复中' }}</div>
    </div>

    <!-- 入场遮罩：纸色渐进淡出；出场反向淡入 -->
    <div class="stage-mask" :data-mode="frameMode" aria-hidden="true"></div>

    <!-- 欢迎横幅：无桌面画面时以居中字标替代 -->
    <div v-if="showBanner" class="welcome" role="status">
      <div v-if="!hasDesktopFrame" class="welcome-mark display">{{ WORDMARK.first }} ∞ {{ WORDMARK.thirdStrong }}</div>
      <div class="welcome-line mono micro muted">SESSION RELEASED / 会话已解封</div>
      <div class="welcome-name display">WELCOME, {{ COPY.welcomeName }}</div>
      <div class="welcome-sub">欢迎回来，会话已恢复至锁定前状态。</div>
      <button type="button" class="relock mono micro" @click="emit('relock')">RE-LOCK / 重新锁定 ↺</button>
    </div>
  </div>
</template>

<style scoped>
.overlay { position: absolute; inset: 0; z-index: 12; pointer-events: none; }
.overlay-frame {
  position: absolute; inset: 0; overflow: hidden;
  background: var(--paper); color: var(--ink);
  transform-origin: center center;
}
.overlay-frame[data-mode="hidden"] { opacity: 0; visibility: hidden; }
.overlay-frame[data-mode="sealing"] { animation: frame-seal 1600ms cubic-bezier(0.16, 1, 0.3, 1) both; }
.overlay-frame[data-mode="releasing"] { animation: frame-seal 1600ms cubic-bezier(0.16, 1, 0.3, 1) reverse both; }
@keyframes frame-seal {
  0% { opacity: 1; transform: scale(1); }
  40% { opacity: 1; transform: scale(0.82) rotate(-0.6deg); }
  100% { opacity: 0; transform: scale(0.22) translate(-160%, -70%) rotate(1.4deg); }
}
.overlay-frame :deep(.corner) { border-color: var(--accent); }
.frame-caption { position: absolute; left: 3%; bottom: 3%; padding: 5px 8px; background: var(--ink); color: var(--paper); font-size: 11px; }
.stage-mask { position: absolute; inset: 0; background: var(--paper); opacity: 0; visibility: hidden; }
.stage-mask[data-mode="sealing"] { visibility: visible; animation: mask-out 1400ms ease-out both; }
.stage-mask[data-mode="releasing"] { visibility: visible; animation: mask-out 1400ms ease-out reverse both; }
@keyframes mask-out { from { opacity: 0.9; } to { opacity: 0; } }

.welcome {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  display: flex; flex-direction: column; align-items: center; gap: 12px;
  padding: 34px 46px; text-align: center;
  background: var(--card); border: 1px solid var(--line); box-shadow: var(--shadow);
  pointer-events: auto;
}
.welcome-mark { font-size: 34px; letter-spacing: 0.04em; }
.welcome-name { font-size: 42px; color: var(--ink); }
.welcome-sub { font-size: 14px; color: var(--muted); }
.relock { margin-top: 10px; padding: 10px 16px; border: 1px solid var(--ink); font-size: 11px; letter-spacing: 0.14em; }
.relock:hover { background: var(--accent); border-color: var(--accent); color: #111214; }
@media (max-width: 520px) { .welcome { padding: 22px; } .welcome-name { font-size: 26px; } }
</style>
