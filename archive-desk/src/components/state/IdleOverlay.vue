<script setup>
/**
 * state/IdleOverlay.vue —— 空闲态（默认 45s）
 * 除品牌带、计时、一行提示外全部滑出画布；背景压暗至 45%；
 * 提示以 455ms 周期呼吸闪烁；任意输入恢复，且该次输入只用于唤醒。
 */
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionStore } from '@/stores/session'

const IDLE_MS = 45000

const route = useRoute()
const session = useSessionStore()

let timer = null

const allow = computed(() => route.meta.idle !== false && session.phase !== 'working')

function arm() {
  clearTimeout(timer)
  if (!allow.value) {
    session.idle = false
    return
  }
  timer = setTimeout(() => {
    if (allow.value) session.idle = true
  }, IDLE_MS)
}

function onActivity(e) {
  if (session.idle) {
    session.idle = false
    // 该次输入只用于唤醒，不继续传递给下面的控件
    if (e && e.cancelable) e.preventDefault()
    if (e) e.stopPropagation()
  }
  arm()
}

watch(allow, arm)

onMounted(() => {
  arm()
  const opts = { capture: true, passive: false }
  window.addEventListener('pointermove', onActivity, { capture: true, passive: true })
  window.addEventListener('pointerdown', onActivity, opts)
  window.addEventListener('keydown', onActivity, opts)
  window.addEventListener('wheel', onActivity, { capture: true, passive: true })
  window.addEventListener('touchstart', onActivity, { capture: true, passive: true })
})

onBeforeUnmount(() => {
  clearTimeout(timer)
  window.removeEventListener('pointermove', onActivity, true)
  window.removeEventListener('pointerdown', onActivity, true)
  window.removeEventListener('keydown', onActivity, true)
  window.removeEventListener('wheel', onActivity, true)
  window.removeEventListener('touchstart', onActivity, true)
})
</script>

<template>
  <div v-if="session.idle" class="idle" aria-live="polite">
    <div class="idle__dim" />
    <div class="idle__hint">
      <span class="idle__zh">任意输入以继续</span>
      <span class="idle__en">INPUT TO RESUME</span>
    </div>
  </div>
</template>

<style scoped>
.idle {
  position: absolute;
  inset: 0;
  z-index: 40;
}

.idle__dim {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
}

.idle__hint {
  position: absolute;
  left: 50%;
  bottom: 12%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  animation: breath 455ms steps(2, end) infinite;
  text-align: center;
}

.idle__zh {
  font-family: var(--font-sans);
  font-size: var(--t15);
  letter-spacing: 4px;
  color: var(--rev);
}

.idle__en {
  font-family: var(--font-mono);
  font-size: var(--t8);
  letter-spacing: 1.6px;
  color: var(--rev);
  opacity: 0.7;
}
</style>
