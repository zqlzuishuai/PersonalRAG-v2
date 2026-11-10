<script setup>
/**
 * 全屏会话锁定界面 —— 主编排层（单文件组件结构）。
 *
 * 关键逻辑总览：
 * 1. 所有状态由 useLockMachine 单点驱动；组件只消费 displayPhase / 派生值，
 *    保证字幕、步骤点、尝试次数、日志与视觉状态严格同步。
 * 2. data-tone="reject" 挂在外壳上 → 全部组件引用的色板 token 整幅反相，
 *    荧光强调统一转警示色（不是局部弹窗）。
 * 3. 画布用 16:9 百分比定位 + 等比 scale；竖屏/窄屏切换紧凑纵向布局，
 *    组件、状态语义与文案不变。
 * 4. 能力开关关闭某项时只 v-if 移除对应组件，绝对定位下其余元素不重排、不补位。
 * 5. 入场 / 出场共用同一组 transition 与关键帧，加/去 .is-revealed 即为镜像。
 * 6. 待机时任意键只唤醒不写入输入；全局键盘处理器 preventDefault 并失焦输入条。
 */
import { reactive, ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useLockMachine } from './composables/useLockMachine'
import { useStageScale } from './composables/useStageScale'
import { DEFAULT_CAPABILITIES, COPY } from './config'

import Wordmark from './components/Wordmark.vue'
import ClockSteps from './components/ClockSteps.vue'
import LeftRail from './components/LeftRail.vue'
import SpecimenCard from './components/SpecimenCard.vue'
import AudioCard from './components/AudioCard.vue'
import ArchivePanel from './components/ArchivePanel.vue'
import InfinitySculpture from './components/InfinitySculpture.vue'
import VerifyRing from './components/VerifyRing.vue'
import WarningBoard from './components/WarningBoard.vue'
import FooterBar from './components/FooterBar.vue'
import Subtitle from './components/Subtitle.vue'
import LeaderLines from './components/LeaderLines.vue'
import StageOverlay from './components/StageOverlay.vue'
import DemoConsole from './components/DemoConsole.vue'

// reactive 会解包 ref/computed，子组件可用 machine.phase 等直接取值。
const machine = reactive(useLockMachine())
const { scale, isCompact } = useStageScale()
const capabilities = reactive({ ...DEFAULT_CAPABILITIES })
const hasDesktopFrame = ref(true)
const revealedTick = ref(false)
let revealTimer

const tone = computed(() => (machine.isRejected ? 'reject' : 'normal'))
const view = computed(() => capabilities.secondaryView ? 'secondary'
  : capabilities.fallbackView ? 'fallback' : 'primary')
const quality = computed(() => capabilities.quality)
const layout = computed(() => (isCompact.value ? 'compact' : 'canvas'))
const silent = computed(() => capabilities.secondaryView)
const effectiveSound = computed(() => machine.soundOn && !silent.value)
const threeD = computed(() => capabilities.threeD && !capabilities.fallbackView)

const showWarning = computed(() => machine.isRejected)
const isIdle = computed(() => machine.displayPhase === 'idle')
const isExiting = computed(() => ['approved', 'exiting'].includes(machine.displayPhase))
const sealing = computed(() => machine.displayPhase === 'entering' && revealedTick.value)
const releasing = computed(() => isExiting.value)
const revealed = computed(() => {
  if (machine.displayPhase === 'entering') return revealedTick.value
  if (isExiting.value) return false
  return true
})
// 入场首帧（桌面画面）期间隐藏分层元素，随后按 --layer 渐进揭示。
const enteringHidden = computed(() => machine.displayPhase === 'entering' && !revealedTick.value)
const styleVars = computed(() => ({ '--stage-scale': String(scale.value) }))

// 入场分层揭示：短延时后统一加 .is-revealed，各元素按 --layer 依次出现。
const scheduleReveal = () => {
  revealedTick.value = false
  clearTimeout(revealTimer)
  revealTimer = setTimeout(() => { revealedTick.value = true }, 240)
}
watch(() => machine.phase, (p) => { if (p === 'entering') scheduleReveal() })

const onGlobalKey = (event) => {
  if (machine.phase === 'idle') {
    // 唤醒键只唤醒、不写入输入：拦截默认行为，输入条在 idle 时已 disabled + 失焦。
    event.preventDefault()
    machine.wake()
    return
  }
  if (event.key === 'Escape') machine.clearSecret()
  machine.noteActivity()
}

onMounted(() => {
  // URL 变量：?view=secondary / ?view=fallback / ?quality=low
  const q = new URLSearchParams(window.location.search)
  if (q.get('view') === 'secondary') capabilities.secondaryView = true
  if (q.get('view') === 'fallback') capabilities.fallbackView = true
  const qQuality = q.get('quality')
  if (['high', 'medium', 'low'].includes(qQuality)) capabilities.quality = qQuality
  // URL 变量：?state=ready|verifying|rejected|... 直达任意状态，便于逐项对照验收
  const qState = q.get('state')
  scheduleReveal()
  if (qState) setTimeout(() => machine.goToPhase(qState), 320)
  window.addEventListener('keydown', onGlobalKey)
})
onBeforeUnmount(() => {
  clearTimeout(revealTimer)
  window.removeEventListener('keydown', onGlobalKey)
})
</script>

<template>
  <div
    class="app-shell"
    :data-tone="tone"
    :data-view="view"
    :data-quality="quality"
    :class="{ 'is-revealed': revealed, 'is-entering': enteringHidden, 'is-exiting': isExiting, 'is-glitch': showWarning, 'is-idle': isIdle }"
  >
    <div class="stage-viewport" :data-layout="layout">
      <main class="stage" :style="styleVars">
        <!-- 左索引竖线：宽 22% 处贯通全高 -->
        <div class="stage-item pos-index-line index-line compact-hide hide-on-secondary hide-on-fallback" aria-hidden="true"></div>

        <div class="stage-item pos-wordmark reveal" style="--layer: 1">
          <Wordmark />
        </div>

        <div class="stage-item pos-clock reveal" style="--layer: 2">
          <ClockSteps
            :clock="machine.clock"
            :elapsed="machine.elapsed"
            :locked-at="machine.lockedAtLabel"
            :active-step="machine.activeStep"
            :step-labels="machine.stepLabels"
            :display-phase="machine.displayPhase"
          />
        </div>

        <!-- 中央状态锚点：雕塑、断续验证环共用同一视觉交点 -->
        <div class="stage-item pos-center" style="--layer: 3">
          <InfinitySculpture
            :display-phase="machine.displayPhase"
            :three-d="threeD"
            :fallback="capabilities.fallbackView"
          />
          <VerifyRing :display-phase="machine.displayPhase" :progress="machine.progress" />
        </div>

        <div v-if="showWarning" class="stage-item pos-warning">
          <WarningBoard :copy="machine.rejectionCopy" :rows="machine.warningRows" :attempts="machine.attempts" />
        </div>

        <!-- 右档案面板：副屏视图保留，且强制静默 -->
        <div class="stage-item pos-archive reveal" style="--layer: 2">
          <ArchivePanel :machine="machine" :silent="silent" :fallback="capabilities.fallbackView" />
        </div>

        <!-- 封存卡片：入场落卡 / 出场反向放大 -->
        <div class="stage-item pos-specimen reveal hide-on-secondary" style="--layer: 4">
          <SpecimenCard
            :display-phase="machine.displayPhase"
            :locked-at="machine.lockedAtLabel"
            :sealing="sealing"
            :releasing="releasing"
          />
        </div>

        <!-- 能力开关：关闭只移除本组件，其余元素不重排、不补位 -->
        <div v-if="capabilities.mediaCard" class="stage-item pos-audio reveal hide-on-secondary" style="--layer: 5">
          <AudioCard :sound-on="effectiveSound" :silent="silent" :display-phase="machine.displayPhase" />
        </div>

        <div class="stage-item pos-rail reveal hide-on-secondary" style="--layer: 3">
          <LeftRail :logs="machine.logs" :active-step="machine.activeStep" :display-phase="machine.displayPhase" />
        </div>

        <div class="stage-item pos-leaders compact-hide hide-on-secondary hide-on-fallback" aria-hidden="true">
          <LeaderLines />
        </div>
        <div class="stage-item pos-signature compact-hide hide-on-secondary">
          <span class="mono micro muted">{{ COPY.signature }}</span>
        </div>

        <div class="stage-item pos-subtitle" style="--layer: 6">
          <Subtitle :subtitle="machine.subtitle" :phase="machine.displayPhase" />
        </div>

        <div class="stage-item pos-footer reveal hide-on-secondary" style="--layer: 6">
          <FooterBar :machine="machine" :capabilities="capabilities" :silent="silent" />
        </div>

        <!-- 入场 / 出场遮罩、桌面画面与欢迎横幅 -->
        <StageOverlay
          :display-phase="machine.displayPhase"
          :release-done="machine.releaseDone"
          :has-desktop-frame="hasDesktopFrame"
          @relock="machine.relock()"
        />
      </main>
    </div>

    <!-- 演示控制层：不属于设计范式，位于舞台之外，不受副屏隐藏规则影响 -->
    <DemoConsole
      :machine="machine"
      :capabilities="capabilities"
      v-model:has-desktop-frame="hasDesktopFrame"
    />
  </div>
</template>
