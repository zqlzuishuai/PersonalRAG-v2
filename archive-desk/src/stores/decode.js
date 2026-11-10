import { defineStore } from 'pinia'

/**
 * stores/decode.js
 * 逐字解码的「只解码一次」登记簿：同一屏内同一段文字不重复抖动。
 */
export const useDecodeStore = defineStore('decode', () => {
  const seen = new Set()

  /** 首次出现返回 true（应当播放解码），已解码过返回 false */
  function claim(key) {
    if (seen.has(key)) return false
    seen.add(key)
    return true
  }

  function reset() {
    seen.clear()
  }

  return { claim, reset }
})
