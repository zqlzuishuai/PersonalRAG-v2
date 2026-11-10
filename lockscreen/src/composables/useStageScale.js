import { ref, onMounted, onUnmounted } from 'vue'
import { SLOT_WIDTH, SLOT_GAP } from '../config'

const BASE_W = 1920
const BASE_H = 1080

/**
 * 画布等比缩放：所有位置以 16:9 画布宽高百分比描述，不绑定绝对尺寸。
 * 桌面模式：scale = min(vw/1920, vh/1080)，贴边元素仍在画布内贴边。
 * 竖屏 / 窄屏：切换紧凑布局（同一套组件与状态语义，纵向可滚动），
 * 这是为移动端适配所做的显式取舍，不改变配色、文案与状态规则。
 */
export function useStageScale() {
  const scale = ref(1)
  const isCompact = ref(false)
  let ro
  const update = () => {
    const vw = window.innerWidth
    const vh = window.innerHeight
    isCompact.value = vw < 900 || vh / Math.max(vw, 1) > 1.15
    scale.value = Math.min(vw / BASE_W, vh / BASE_H)
  }
  onMounted(() => {
    update()
    window.addEventListener('resize', update, { passive: true })
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(update)
      ro.observe(document.documentElement)
    }
  })
  onUnmounted(() => {
    window.removeEventListener('resize', update)
    if (ro) ro.disconnect()
  })
  return { scale, isCompact, update }
}

/**
 * 输入格数按可用宽度自适应折叠：超出可见格数的部分以「+n」呈现。
 * 监听输入条自身宽度，窗口缩放与紧凑布局切换都会重新计算。
 */
export function useSlotCapacity(elRef, reserve = 90) {
  const capacity = ref(8)
  let ro
  const measure = () => {
    const el = elRef.value
    if (!el) return
    const usable = Math.max(SLOT_WIDTH, el.clientWidth - reserve)
    capacity.value = Math.max(1, Math.floor((usable + SLOT_GAP) / (SLOT_WIDTH + SLOT_GAP)))
  }
  onMounted(() => {
    measure()
    window.addEventListener('resize', measure, { passive: true })
    if (typeof ResizeObserver !== 'undefined' && elRef.value) {
      ro = new ResizeObserver(measure)
      ro.observe(elRef.value)
    }
  })
  onUnmounted(() => {
    window.removeEventListener('resize', measure)
    if (ro) ro.disconnect()
  })
  return { capacity, measure }
}
