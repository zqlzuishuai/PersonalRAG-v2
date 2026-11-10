<script setup>
/**
 * fx/GlitchTear.vue —— 翻幕遮罩
 * 幕切换必须在单帧完成，用一次 300ms 的故障撕裂遮盖：
 * 横向块位移 + 轻微色散 + 亮度跳变。不允许渐变过渡。
 */
import { ref, watch } from 'vue'
import { useCurtainStore } from '@/stores/curtain'

const curtain = useCurtainStore()
const slabs = ref([])

function build() {
  slabs.value = Array.from({ length: 11 }, (_, i) => {
    const r = Math.random()
    return {
      i,
      top: +(Math.random() * 94).toFixed(2),
      h: +(1.2 + Math.random() * 7).toFixed(2),
      tx: Math.round((Math.random() * 2 - 1) * 52),
      delay: Math.round(Math.random() * 110),
      dur: 200 + Math.round(Math.random() * 90),
      kind: r > 0.62 ? 'diff' : r > 0.3 ? 'blk' : 'bg',
    }
  })
}

watch(
  () => curtain.tearing,
  (on) => {
    if (on) build()
  },
)
</script>

<template>
  <div v-if="curtain.tearing" class="tear" aria-hidden="true">
    <span
      v-for="s in slabs"
      :key="s.i"
      class="tear__slab"
      :class="`tear__slab--${s.kind}`"
      :style="{
        top: `${s.top}%`,
        height: `${s.h}%`,
        animationDelay: `${s.delay}ms`,
        animationDuration: `${s.dur}ms`,
        '--tx': `${s.tx}px`,
      }"
    />
    <span class="tear__flash" />
  </div>
</template>

<style scoped>
.tear {
  position: fixed;
  inset: 0;
  z-index: 90;
  overflow: hidden;
  pointer-events: none;
}

.tear__slab {
  position: absolute;
  left: -14%;
  width: 128%;
  animation-name: tear-slab;
  animation-timing-function: steps(3, end);
  animation-fill-mode: both;
}

.tear__slab--blk {
  background: var(--blk);
  opacity: 0.92;
}

.tear__slab--bg {
  background: var(--bg);
  opacity: 0.95;
}

.tear__slab--diff {
  background: #7c7c7c;
  mix-blend-mode: difference;
}

.tear__flash {
  position: absolute;
  inset: 0;
  background: #ffffff;
  animation: flash-lum 300ms steps(1, end) both;
}
</style>
