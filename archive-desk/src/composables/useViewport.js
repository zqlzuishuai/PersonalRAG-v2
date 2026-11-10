import { onBeforeUnmount, onMounted, reactive } from 'vue'

/**
 * composables/useViewport.js
 * 响应式的唯一实现：
 * 以 1920×1080 为唯一设计基准，整体等比缩放 k = min(vw/1920, vh/1080)，
 * 设计画布反向撑开为 (vw/k) × (vh/k) —— 因此铺满、无黑边，且不重排、不换行。
 * 窄屏（< 900px）放弃缩放，改为单列（字号阶梯整体 ×0.85，见 base.css）。
 */
const BASE_W = 1920
const BASE_H = 1080
const NARROW = 900

export const viewport = reactive({
  mode: 'stage', // 'stage' 等比缩放 | 'column' 单列
  k: 1,
  w: BASE_W,
  h: BASE_H,
  ready: false,
})

function measure() {
  if (typeof window === 'undefined') return
  const vw = window.innerWidth
  const vh = window.innerHeight

  if (vw < NARROW) {
    viewport.mode = 'column'
    viewport.k = 1
    viewport.w = vw
    viewport.h = vh
    viewport.ready = true
    return
  }

  const k = Math.min(vw / BASE_W, vh / BASE_H)
  viewport.mode = 'stage'
  viewport.k = Math.round(k * 10000) / 10000
  viewport.w = Math.ceil(vw / k)
  viewport.h = Math.ceil(vh / k)
  viewport.ready = true
}

let users = 0

export function useViewport() {
  onMounted(() => {
    if (users === 0) {
      measure()
      window.addEventListener('resize', measure, { passive: true })
      window.addEventListener('orientationchange', measure, { passive: true })
    }
    users += 1
  })

  onBeforeUnmount(() => {
    users -= 1
    if (users === 0) {
      window.removeEventListener('resize', measure)
      window.removeEventListener('orientationchange', measure)
    }
  })

  return viewport
}
