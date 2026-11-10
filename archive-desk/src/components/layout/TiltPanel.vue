<script setup>
/**
 * layout/TiltPanel.vue —— 主面板
 * 贴右边距，带一层偏移 16px 的次级底板；4–6° 常驻倾角，随指针在 ±4° 内偏转。
 * 默认高度随内容（先决定信息，再决定形态）；fill 时撑满该栏。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { viewport } from '@/composables/useViewport'

const props = defineProps({
  fill: { type: Boolean, default: false },
})

const BASE = -4.4
const rot = ref(BASE)
const stage = computed(() => viewport.mode === 'stage')

let raf = 0
let nx = 0

function apply() {
  raf = 0
  rot.value = BASE + nx * 4
}

function onMove(e) {
  nx = (e.clientX / window.innerWidth) * 2 - 1
  if (!raf) raf = requestAnimationFrame(apply)
}

onMounted(() => {
  window.addEventListener('pointermove', onMove, { passive: true })
})

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onMove)
  if (raf) cancelAnimationFrame(raf)
})
</script>

<template>
  <div class="tilt" :class="{ 'tilt--fill': props.fill }" :style="{ '--rot': `${rot}deg` }">
    <div class="tilt__plate" aria-hidden="true" />
    <div class="tilt__body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.tilt {
  position: relative;
  width: 100%;
  min-height: 0;
}

.tilt--fill {
  height: 100%;
}

.tilt__plate,
.tilt__body {
  border: 1px solid var(--line);
  transform-origin: 50% 50%;
}

.tilt__plate {
  position: absolute;
  inset: 0;
  background: var(--card);
  transform: translate(16px, 16px) rotate(calc(var(--rot) - 1.6deg));
}

.tilt__body {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--card);
  transform: rotate(var(--rot));
  overflow: hidden;
}

.tilt--fill .tilt__body {
  height: 100%;
}

/* 窄屏：去倾角、去底板，改为常规卡片 */
.mode-column .tilt__plate {
  display: none;
}

.mode-column .tilt__body {
  transform: none;
}
</style>
