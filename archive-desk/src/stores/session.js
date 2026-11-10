import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { credentials } from '@/data/registry'

/**
 * stores/session.js
 * 会话与四态：常态 idle / 进行中 working / 失败 failure / 成功 success
 * 阶段 stage 0–3 决定竖轴上那枚标记块的高度（全局唯一的位置型状态指示）。
 */
export const useSessionStore = defineStore('session', () => {
  const phase = ref('idle')
  const stage = ref(0)
  const credential = ref('')
  const attempts = ref(3)
  const reason = ref('')
  const admit = ref(false)
  const stamp = ref('')
  const idle = ref(false) // 空闲态：默认 45s，可配

  const busy = computed(() => phase.value === 'working')
  const locked = computed(() => attempts.value <= 0)
  const stageLabel = computed(() => ['VERIFY', 'RETRIEVE', 'CONSULT', 'RESEAL'][stage.value] || 'VERIFY')
  const stageZh = computed(() => ['核验', '检索', '调阅', '归档'][stage.value] || '核验')

  function setStage(i) {
    stage.value = Math.max(0, Math.min(3, i))
  }

  function setCredential(code) {
    credential.value = code
  }

  /** 校验：凭据必须在签发簿内，且剩余尝试次数大于 0 */
  function check(code) {
    const c = String(code || '').toUpperCase()
    if (locked.value) return { ok: false, reason: `凭据 ${c || '——'} 已被冻结 · 剩余尝试 0 次` }
    if (c.length < 4) return { ok: false, reason: `凭据位数不足（${c.length}/4）· 未提交至签发簿` }
    const hit = credentials.find((item) => item.code === c)
    if (!hit) {
      attempts.value -= 1
      return {
        ok: false,
        reason: `凭据 ${c} 未登记于签发簿 · 剩余尝试 ${attempts.value} 次`,
      }
    }
    return { ok: true, holder: hit.holder, level: hit.level }
  }

  function toWorking() {
    phase.value = 'working'
    reason.value = ''
  }

  function toSuccess(holder = '') {
    phase.value = 'success'
    admit.value = true
    stamp.value = holder
  }

  function toFailure(text) {
    phase.value = 'failure'
    reason.value = text
  }

  function reset() {
    if (phase.value === 'failure') phase.value = 'idle'
  }

  function hardReset() {
    phase.value = 'idle'
    credential.value = ''
    attempts.value = 3
    reason.value = ''
    admit.value = false
    idle.value = false
  }

  return {
    phase,
    stage,
    credential,
    attempts,
    reason,
    admit,
    stamp,
    idle,
    busy,
    locked,
    stageLabel,
    stageZh,
    setStage,
    setCredential,
    check,
    toWorking,
    toSuccess,
    toFailure,
    reset,
    hardReset,
  }
})
