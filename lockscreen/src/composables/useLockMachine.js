import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  SUBTITLES, REJECTION, warningRecords, MAX_SECRET_LENGTH,
  PHASE_SEQUENCE, STEPS,
} from '../config'

const pad = (n) => String(n).padStart(2, '0')
const hhmmss = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`

/**
 * 凭据判定（演示规则，配置与界面均不含任何凭据明文）：
 * - >=10 位且含大写字母与数字 → 通过（授权）
 * - >=6  位且含大写字母与数字 → 凭据通过但会话被策略拒绝
 * - 其余                      → 凭据被拒
 * 生产环境应替换为服务端校验；此处只负责驱动三态视觉。
 */
export function classifyCredential(value) {
  const hasUpper = /[A-Z]/.test(value)
  const hasDigit = /\d/.test(value)
  if (value.length >= 10 && hasUpper && hasDigit) return 'grant'
  if (value.length >= 6 && hasUpper && hasDigit) return 'policy'
  return 'deny'
}

/**
 * 会话锁定状态机：状态数量与顺序固定，typing 由 ready + 非空输入派生。
 * 入场 → 就绪 → (输入) → 验证中 → 拒绝 / 授权 → 出场；待机可并行进入。
 */
export function useLockMachine() {
  const phase = ref('entering')
  const secret = ref('')
  const forcedOutcome = ref(null) // 仅演示注入用，界面不渲染明文
  const attempts = ref(0)
  const rejectReason = ref(null) // 'credential' | 'policy'
  const progress = ref(0)
  const overflow = ref(false)
  const releaseDone = ref(false)
  const soundOn = ref(true)
  const logs = ref([])
  const now = ref(new Date())
  const lockedAt = ref(new Date())
  const lastActivity = ref(Date.now())
  const idleAfterMs = 45000

  // 统一收纳延时器，卸载时全部清理，避免状态回写已销毁组件。
  const timers = new Set()
  const later = (fn, ms) => {
    const id = setTimeout(() => { timers.delete(id); fn() }, ms)
    timers.add(id)
    return id
  }

  const clock = computed(() => hhmmss(now.value))
  const lockedAtLabel = computed(() => hhmmss(lockedAt.value))
  const lockedDate = computed(() => {
    const d = lockedAt.value
    return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`
  })
  const elapsed = computed(() => {
    const s = Math.max(0, Math.floor((now.value - lockedAt.value) / 1000))
    return `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`
  })

  // 关键逻辑：显示态与视觉态同步的唯一出口。
  const displayPhase = computed(() =>
    phase.value === 'ready' && secret.value.length > 0 ? 'typing' : phase.value,
  )
  const isRejected = computed(() => displayPhase.value === 'rejected')
  const subtitle = computed(() => {
    if (displayPhase.value === 'rejected' && rejectReason.value === 'policy') {
      return { zh: REJECTION.policy.zh, en: REJECTION.policy.en }
    }
    return SUBTITLES[displayPhase.value] || SUBTITLES.ready
  })
  const activeStep = computed(() => {
    switch (displayPhase.value) {
      case 'entering': return 0
      case 'verifying': case 'rejected': return 2
      case 'approved': case 'exiting': return 3
      default: return 1
    }
  })
  const stepLabels = STEPS
  const warningRows = computed(() =>
    warningRecords(rejectReason.value || 'credential', attempts.value, lockedAtLabel.value),
  )
  const rejectionCopy = computed(() => REJECTION[rejectReason.value || 'credential'])
  const canSubmit = computed(() =>
    phase.value === 'ready' && secret.value.length > 0 && !overflow.value,
  )
  const maskedLength = computed(() => secret.value.length)
  const hiddenCount = computed(() => Math.max(0, maskedLength.value - 0)) // 组件内按 capacity 折叠

  const pushLog = (code) => {
    logs.value = [{ t: hhmmss(new Date()), code }, ...logs.value].slice(0, 7)
  }
  const noteActivity = () => { lastActivity.value = Date.now() }

  const setSecret = (value) => {
    if (phase.value !== 'ready') return
    noteActivity()
    if (value.length > MAX_SECRET_LENGTH) {
      // 超长输入：明确拒绝并截断，不静默吞掉。
      overflow.value = true
      secret.value = value.slice(0, MAX_SECRET_LENGTH)
      pushLog(`OVERFLOW · LIMIT ${MAX_SECRET_LENGTH}`)
      return
    }
    overflow.value = false
    secret.value = value
  }
  const clearSecret = () => {
    if (phase.value !== 'ready') return
    secret.value = ''
    overflow.value = false
    noteActivity()
    pushLog('INPUT · CLEARED')
  }

  const reject = (reason) => {
    attempts.value += 1
    rejectReason.value = reason
    phase.value = 'rejected'
    progress.value = 0
    pushLog(`${reason === 'policy' ? 'POLICY' : 'AUTH'} · REJECTED / ${pad(attempts.value)}`)
    // 短时故障闪动后自动恢复就绪（全局反相同时撤除）。
    later(() => {
      if (phase.value !== 'rejected') return
      phase.value = 'ready'
      secret.value = ''
      overflow.value = false
      rejectReason.value = null
      noteActivity()
      pushLog('INPUT · RESET')
    }, 3000)
  }

  const approve = () => {
    phase.value = 'approved'
    pushLog('AUTH · ACCEPTED')
    later(() => {
      phase.value = 'exiting'
      pushLog('FRAME · RESTORING')
      later(() => {
        releaseDone.value = true
        pushLog('SESSION · RELEASED')
      }, 1500)
    }, 1200)
  }

  const submit = () => {
    // 空凭据不提交：校验前置，按钮同时 disabled。
    if (phase.value !== 'ready') return
    if (!secret.value.length) { pushLog('EMPTY · NOT SUBMITTED'); return }
    if (overflow.value) { pushLog('OVERFLOW · NOT SUBMITTED'); return }
    phase.value = 'verifying'
    progress.value = 0
    rejectReason.value = null
    pushLog('VERIFY / BEGIN')
    const tickMs = 60
    const totalMs = 1900
    let spent = 0
    const step = () => {
      if (phase.value !== 'verifying') return
      spent += tickMs
      progress.value = Math.min(100, Math.round((spent / totalMs) * 100))
      if (spent < totalMs) { later(step, tickMs); return }
      const outcome = forcedOutcome.value || classifyCredential(secret.value)
      forcedOutcome.value = null
      if (outcome === 'grant') approve()
      else reject(outcome === 'policy' ? 'policy' : 'credential')
    }
    later(step, tickMs)
  }

  /** 演示注入：只生成占位字符决定方块数量，结果由 forcedOutcome 指定，全程无凭据明文。 */
  const demo = (kind) => {
    if (phase.value !== 'ready') return
    forcedOutcome.value = kind // 'grant' | 'policy' | 'deny'
    secret.value = '•'.repeat(kind === 'grant' ? 10 : kind === 'policy' ? 7 : 4)
    overflow.value = false
    pushLog(`SIM · ${String(kind).toUpperCase()}`)
    submit()
  }

  const enterIdle = () => {
    if (phase.value !== 'ready') return
    phase.value = 'idle'
    pushLog('TERMINAL · IDLE')
  }
  /** 唤醒键只唤醒、不写入输入：App 层会 preventDefault 并阻止输入聚焦。 */
  const wake = () => {
    if (phase.value !== 'idle') return
    phase.value = 'ready'
    noteActivity()
    pushLog('TERMINAL · AWAKE')
  }

  const relock = () => {
    releaseDone.value = false
    phase.value = 'entering'
    secret.value = ''
    attempts.value = 0
    rejectReason.value = null
    progress.value = 0
    lockedAt.value = new Date()
    logs.value = []
    pushLog('FRAME · SEAL REQUESTED')
    later(() => { phase.value = 'ready'; noteActivity(); pushLog('INPUT · ARMED') }, 2300)
  }

  /** 演示控制台：直接跳转任意状态以逐项验收（不改变状态集合）。 */
  const goToPhase = (target) => {
    if (!PHASE_SEQUENCE.includes(target)) return
    timers.forEach(clearTimeout)
    timers.clear()
    releaseDone.value = false
    if (target === 'typing') {
      phase.value = 'ready'
      secret.value = '•'.repeat(6)
    } else if (target === 'rejected') {
      attempts.value += 1
      rejectReason.value = rejectReason.value || 'credential'
      phase.value = 'rejected'
    } else if (target === 'idle') {
      phase.value = 'idle'
    } else if (target === 'verifying') {
      phase.value = 'verifying'
      progress.value = 62 // 静态验收帧：进度条与环保持可见
    } else if (target === 'exiting') {
      phase.value = 'exiting'
      releaseDone.value = true
    } else {
      phase.value = target
    }
    noteActivity()
    pushLog(`SIM · STATE ${String(target).toUpperCase()}`)
  }

  const confirmPower = (id) => pushLog(`POWER · ${String(id).toUpperCase()} / CONFIRMED`)
  const toggleSound = () => { soundOn.value = !soundOn.value; pushLog(`SOUND · ${soundOn.value ? 'ON' : 'MUTED'}`) }

  let ticker
  onMounted(() => {
    pushLog('FRAME · SEAL REQUESTED')
    later(() => { phase.value = 'ready'; noteActivity(); pushLog('INPUT · ARMED') }, 2300)
    ticker = setInterval(() => {
      now.value = new Date()
      if (phase.value === 'ready' && !releaseDone.value &&
          Date.now() - lastActivity.value > idleAfterMs) enterIdle()
    }, 1000)
  })
  onUnmounted(() => {
    timers.forEach(clearTimeout)
    timers.clear()
    clearInterval(ticker)
  })

  return {
    phase, displayPhase, isRejected, secret, attempts, rejectReason, progress,
    overflow, releaseDone, soundOn, logs, clock, lockedAtLabel, lockedDate, elapsed,
    subtitle, activeStep, stepLabels, warningRows, rejectionCopy, canSubmit,
    maskedLength, hiddenCount, pushLog, noteActivity, setSecret, clearSecret,
    submit, demo, enterIdle, wake, relock, goToPhase, confirmPower, toggleSound,
  }
}
