<script setup>
/**
 * App.vue —— 三条横带 + 一条竖轴的全局框架
 * 品牌带（上）/ 主带（中，22%·40%·38% 三栏）/ 状态带（下）；
 * 视图只负责主带里的内容，框架与阶段指示全站唯一。
 */
import { computed, onMounted, watch, watchEffect } from 'vue'
import { useRoute } from 'vue-router'

import { useViewport } from '@/composables/useViewport'
import { useCurtainStore } from '@/stores/curtain'
import { useSessionStore } from '@/stores/session'

import BrandLockup from '@/components/layout/BrandLockup.vue'
import ClockBlock from '@/components/layout/ClockBlock.vue'
import StatusBand from '@/components/layout/StatusBand.vue'
import AxisRail from '@/components/layout/AxisRail.vue'
import GlitchTear from '@/components/fx/GlitchTear.vue'
import IdleOverlay from '@/components/state/IdleOverlay.vue'

const vp = useViewport()
const curtain = useCurtainStore()
const session = useSessionStore()
const route = useRoute()

const canvasStyle = computed(() =>
  vp.mode === 'column'
    ? {}
    : { width: `${vp.w}px`, height: `${vp.h}px`, transform: `scale(${vp.k})` },
)

// 幕值写回根元素：所有颜色由它整体插值，不做局部改色
watchEffect(() => {
  document.documentElement.style.setProperty('--curtain', String(curtain.value))
})

// 字号阶梯的倍数也必须写在 :root —— 自定义属性里的 var() 只在定义处求值
watchEffect(() => {
  document.documentElement.style.setProperty('--ts', vp.mode === 'column' ? '0.85' : '1')
})

// 路由决定阶段：竖轴上的标记块随之跳位
watch(
  () => route.meta.stage,
  (s) => {
    if (typeof s === 'number') session.setStage(s)
  },
  { immediate: true },
)

// 调试 / 分享用：?ink=1 直接进入墨幕
watch(
  () => route.query.ink,
  (v) => {
    if (v) curtain.apply(1)
  },
  { immediate: true },
)
</script>

<template>
  <div class="stage" :class="`mode-${vp.mode}`">
    <div class="canvas" :class="{ 'is-idle': session.idle }" :style="canvasStyle">
      <header class="band band--brand">
        <BrandLockup />
        <ClockBlock />
      </header>

      <main class="band band--main">
        <RouterView />
      </main>

      <footer class="band band--status">
        <StatusBand />
      </footer>

      <AxisRail />
      <IdleOverlay />
    </div>

    <GlitchTear />
  </div>
</template>
