import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

/**
 * stores/curtain.js
 * 「幕值」：0 = 纸幕，1 = 墨幕。两幕是同一套角色的两组取值，整体插值。
 * 切换必须单帧完成，由一次 300ms 的故障撕裂遮盖（见 GlitchTear.vue）。
 */
export const useCurtainStore = defineStore('curtain', () => {
  const value = ref(0)
  const tearing = ref(false)
  let timer = null

  const isInk = computed(() => value.value > 0.5)

  function apply(v) {
    value.value = Math.min(1, Math.max(0, Number(v) || 0))
  }

  /** 带撕裂遮盖的翻幕（单帧换色，不用渐变过渡） */
  function flip(target) {
    const next = Math.min(1, Math.max(0, target))
    if (next === value.value) return
    tearing.value = false
    // 下一帧重启动画，保证撕裂能覆盖这次换色
    requestAnimationFrame(() => {
      apply(next)
      tearing.value = true
      clearTimeout(timer)
      timer = setTimeout(() => {
        tearing.value = false
      }, 320)
    })
  }

  function toggle() {
    flip(isInk.value ? 0 : 1)
  }

  return { value, tearing, isInk, apply, flip, toggle }
})
