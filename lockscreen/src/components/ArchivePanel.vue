<script setup>
/**
 * 右侧磨砂档案面板（核心交互区）。
 * 关键逻辑：
 * 1. 凭据只以等宽白色方块呈现，隐藏 input 捕获键盘，界面绝不渲染明文。
 * 2. 格数按容器宽度自适应折叠为「+n」；超长输入明确拒绝；空凭据不提交。
 * 3. 荧光焦点线、闪烁光标、Alt+←/→ 组内焦点环绕；原生 Tab 保持全局可达。
 * 4. 验证中：照片位扫描线、提交按钮转警示底并改待办文案；拒绝时输入条抖动。
 * 5. 降级视图：去掉磨砂/暗纹/幽灵字，保留同色系与状态语义。
 */
import { ref, computed, watch, nextTick } from 'vue'
import { IDENTITY, COPY, field, MAX_SECRET_LENGTH } from '../config'
import { useSlotCapacity } from '../composables/useStageScale'

const props = defineProps({
  machine: { type: Object, required: true }, // reactive(useLockMachine())，ref 已解包
  silent: { type: Boolean, default: false },
  fallback: { type: Boolean, default: false },
})

const inputRow = ref(null)
const hiddenInput = ref(null)
const clearBtn = ref(null)
const submitBtn = ref(null)
const focused = ref(false)
const { capacity } = useSlotCapacity(inputRow, 128)

const m = computed(() => props.machine)
const length = computed(() => m.value.maskedLength)
const visibleCount = computed(() => Math.min(capacity.value, length.value))
const hiddenCount = computed(() => Math.max(0, length.value - visibleCount.value))
const isVerifying = computed(() => m.value.displayPhase === 'verifying')
const isRejected = computed(() => m.value.displayPhase === 'rejected')
const isReady = computed(() => m.value.phase === 'ready')
const submitLabel = computed(() => {
  if (isVerifying.value) return COPY.verifying
  if (isRejected.value) return 'RETRY / 重试'
  if (m.value.displayPhase === 'approved' || m.value.displayPhase === 'exiting') return 'RELEASED / 已解封'
  return COPY.submit
})
const hint = computed(() => {
  if (m.value.overflow) return { text: `INPUT OVERFLOW · 已超出 ${MAX_SECRET_LENGTH} 格上限，拒绝继续写入`, warn: true }
  if (!length.value && isReady.value) return { text: 'EMPTY · 空凭据不提交', warn: false }
  if (length.value) return { text: `LEN ${String(length.value).padStart(2, '0')} · PLAINTEXT SUPPRESSED`, warn: false }
  return { text: 'INPUT DISABLED / 输入已停用', warn: false }
})
const rows = computed(() => [
  ['OPERATOR', field(IDENTITY.operator)],
  ['HOST', field(IDENTITY.host)],
  ['SESSION', field(IDENTITY.session)],
  ['KEYBOARD', field(IDENTITY.keyboard)],
])
const rings = computed(() => [
  m.value.displayPhase !== 'entering',
  m.value.displayPhase === 'verifying' || m.value.displayPhase === 'approved',
  m.value.displayPhase === 'approved' || m.value.displayPhase === 'exiting',
])

// 输入处理：超长时状态机会截断，这里同步 DOM 值，避免真实输入与掩码不一致。
const onInput = (event) => {
  m.value.setSecret(event.target.value)
  event.target.value = m.value.secret
}
// preventScroll：移动端自动聚焦不会把页面滚到输入条，保持纵向布局从顶部开始。
const focusInput = () => { if (!props.silent && isReady.value) hiddenInput.value?.focus({ preventScroll: true }) }
const clearSecret = (event) => {
  event?.stopPropagation()
  m.value.clearSecret()
  focusInput()
}
const submit = () => {
  if (m.value.canSubmit && isReady.value) m.value.submit()
}

// 焦点环绕：Alt+←/→ 在 [输入框 / 清空 / 提交] 三项间循环；
// 不使用 Tab 拦截，保证页脚电源项等所有交互项仍可由原生 Tab 到达。
const cycleFocus = (event) => {
  if (!event.altKey || (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight')) return
  event.preventDefault()
  const items = [hiddenInput.value, clearBtn.value, submitBtn.value].filter(Boolean)
  const idx = items.indexOf(document.activeElement)
  const delta = event.key === 'ArrowRight' ? 1 : -1
  const next = (idx < 0 ? 0 : (idx + delta + items.length) % items.length)
  items[next].focus()
}

// 就绪时自动聚焦输入条（仅当用户当前没有操作其它控件）；待机时主动失焦，
// 保证「唤醒键只唤醒、不写入输入」。
watch(() => m.value.phase, async (phase) => {
  await nextTick()
  if (phase === 'ready' && !props.silent && document.activeElement === document.body) {
    hiddenInput.value?.focus({ preventScroll: true })
  }
  if (phase === 'idle') hiddenInput.value?.blur()
})
</script>

<template>
  <section class="archive stage-card" :class="{ 'is-fallback': fallback }" aria-label="身份档案与授权">
    <!-- 磨砂面板装饰：白色斜边高光、六边形暗纹、超大低对比幽灵字 -->
    <span class="bevel" aria-hidden="true"></span>
    <span class="ghost-word display" aria-hidden="true">ARCHIVE</span>
    <span class="hex-pattern" aria-hidden="true"></span>

    <header class="arc-head mono micro">
      <span>{{ COPY.archive }}</span>
      <span class="tag" :class="isRejected ? 'tag--warn' : 'tag--accent'">
        {{ isRejected ? 'LOCKED' : isVerifying ? 'SCANNING' : 'SEALED' }}
      </span>
    </header>

    <div class="arc-top">
      <!-- 照片位与保密标 -->
      <div class="photo" aria-hidden="true">
        <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">
          <defs>
            <pattern id="arc-dots" width="4" height="4" patternUnits="userSpaceOnUse">
              <circle cx="1.4" cy="1.4" r="1.05" fill="var(--ink)" opacity="0.7" />
            </pattern>
          </defs>
          <rect width="100" height="100" fill="var(--card)" />
          <path d="M50 20c9 0 15 7 15 17 0 7-4 12-8 15 13 3 22 12 24 27H19c2-15 11-24 24-27-4-3-8-8-8-15 0-10 6-17 15-17z" fill="url(#arc-dots)" />
        </svg>
        <span class="photo-stamp mono">{{ COPY.confidential }}</span>
        <span v-if="isVerifying" class="photo-scan"></span>
      </div>

      <div class="arc-identity">
        <div class="badge mono micro">
          <span class="badge-mark">∞</span> IDENTITY BLOCK / 04
        </div>
        <div class="black-name">{{ field(IDENTITY.operator) }}</div>
        <div class="file-card mono micro">
          <div class="ellipsis">{{ field(IDENTITY.fileCode) }}</div>
          <div class="muted">LOCK {{ m.lockedAtLabel }} · {{ m.lockedDate }}</div>
          <div class="muted">DUR {{ m.elapsed }} · ATT {{ String(m.attempts).padStart(2, '0') }}</div>
        </div>
        <div class="rings" aria-hidden="true">
          <svg v-for="(on, i) in rings" :key="i" viewBox="0 0 40 40">
            <circle cx="20" cy="20" r="14" fill="none" stroke="var(--line)" stroke-width="2" />
            <circle cx="20" cy="20" r="14" fill="none" :stroke="on ? 'var(--accent)' : 'transparent'"
                    stroke-width="2" stroke-dasharray="22 66" transform="rotate(-90 20 20)" />
          </svg>
          <span class="mono micro muted">STATUS RINGS</span>
        </div>
      </div>
    </div>

    <div class="data-table mono micro">
      <div v-for="([k, v], i) in rows" :key="k" class="data-row">
        <span class="muted">{{ String(i + 1).padStart(2, '0') }} · {{ k }}</span>
        <span class="ellipsis">{{ v }}</span>
      </div>
    </div>

    <!-- 授权输入条 -->
    <div class="authorize">
      <div class="auth-label mono micro">
        <span>{{ COPY.authorize }}</span>
        <span class="muted">{{ String(m.attempts).padStart(2, '0') }} / 99</span>
      </div>

      <div
        ref="inputRow"
        class="input-row"
        :class="{ 'is-focused': focused, 'is-rejected': isRejected, 'is-busy': isVerifying, 'is-fallback': fallback }"
        @click="focusInput"
        @keydown="cycleFocus"
      >
        <div class="slots" aria-hidden="true">
          <i v-for="i in visibleCount" :key="i" class="slot"></i>
          <span v-if="hiddenCount" class="fold mono">+{{ hiddenCount }}</span>
          <span v-if="focused && isReady" class="caret"></span>
          <span v-if="!length && !isVerifying" class="placeholder mono">INPUT / 输入</span>
        </div>

        <!-- 真实输入：覆盖整条但完全透明，只负责键盘与可访问性；明文永不渲染 -->
        <input
          ref="hiddenInput"
          class="secret-input"
          type="password"
          autocomplete="off"
          autocapitalize="off"
          spellcheck="false"
          :value="m.secret"
          :disabled="!isReady || silent"
          :aria-label="'授权凭据输入，已输入 ' + length + ' 个字符'"
          @input="onInput"
          @focus="focused = true"
          @blur="focused = false"
          @keydown.enter.prevent="submit"
          @keydown.esc.prevent="clearSecret"
        />

        <button ref="clearBtn" type="button" class="clear mono micro" :disabled="!length"
                aria-label="清空输入" @click="clearSecret">CLR</button>
        <span class="focus-underline"></span>
      </div>

      <!-- 校验提示：空凭据、超长拒绝都给出明确事实陈述 -->
      <p class="hint mono micro" :class="{ warn: hint.warn }" role="status">{{ hint.text }}</p>

      <button
        ref="submitBtn"
        type="button"
        class="submit mono"
        :class="{ busy: isVerifying }"
        :disabled="!m.canSubmit || silent"
        @click="submit"
      >
        <span>{{ submitLabel }}</span>
        <span class="submit-arrow" aria-hidden="true">→</span>
      </button>
      <div class="progress" aria-hidden="true">
        <i :style="{ width: `${m.progress}%` }"></i>
      </div>
    </div>
  </section>
</template>

<style scoped>
.archive {
  position: relative;
  height: 100%;
  padding: 22px 24px;
  overflow: hidden;
  background: var(--panel);
  border: 1px solid var(--panel-edge);
  backdrop-filter: var(--blur);
  -webkit-backdrop-filter: var(--blur);
  box-shadow: var(--shadow);
}
.bevel {
  position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(135deg, rgba(255,255,255,0.85) 0 2px, transparent 2px 100%);
  border-top: 1px solid rgba(255,255,255,0.9);
  border-left: 1px solid rgba(255,255,255,0.75);
}
.hex-pattern {
  position: absolute; inset: 0; pointer-events: none; opacity: 0.5;
  background-image:
    repeating-linear-gradient(60deg, transparent 0 22px, var(--line-soft) 22px 23px),
    repeating-linear-gradient(-60deg, transparent 0 22px, var(--line-soft) 22px 23px);
  mask-image: linear-gradient(to left, black, transparent 62%);
}
.ghost-word {
  position: absolute; right: -4%; bottom: 2%;
  font-size: 180px; color: var(--ink); opacity: 0.035; white-space: nowrap; pointer-events: none;
}
.arc-head { position: relative; display: flex; justify-content: space-between; align-items: center; gap: 10px; padding-bottom: 12px; border-bottom: 1px solid var(--line); }
.arc-top { position: relative; display: grid; grid-template-columns: 128px 1fr; gap: 18px; margin-top: 16px; }
.photo { position: relative; height: 132px; border: 1px solid var(--line); overflow: hidden; background: var(--card); }
.photo svg { width: 100%; height: 100%; display: block; }
.photo-stamp { position: absolute; left: 0; bottom: 0; padding: 3px 6px; font-size: 9px; background: var(--warn); color: #111214; }
.photo-scan { position: absolute; left: 0; right: 0; height: 2px; background: var(--accent); box-shadow: 0 0 10px var(--accent); animation: scan 1.6s linear infinite; }
.arc-identity { min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.badge { display: flex; align-items: center; gap: 8px; color: var(--muted); }
.badge-mark { color: var(--accent); font-size: 16px; }
.black-name { background: var(--ink); color: var(--paper); padding: 7px 10px; font-family: var(--font-display); font-weight: 900; font-size: 19px; letter-spacing: 0.02em; }
.file-card { border: 1px solid var(--line); padding: 7px 9px; display: flex; flex-direction: column; gap: 3px; font-size: 10px; }
.rings { display: flex; align-items: center; gap: 8px; }
.rings svg { width: 26px; height: 26px; }
.rings .mono { font-size: 9px; margin-left: 4px; }
.data-table { position: relative; margin-top: 14px; border-top: 1px solid var(--line); }
.data-row { display: grid; grid-template-columns: 42% 58%; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--line-soft); font-size: 11px; }
.authorize { position: relative; margin-top: 16px; }
.auth-label { display: flex; justify-content: space-between; margin-bottom: 8px; }
.input-row {
  position: relative; display: flex; align-items: center;
  height: 52px; padding: 0 10px;
  border: 1px solid var(--ink); background: var(--card);
  transition: box-shadow 320ms ease, border-color 320ms ease;
}
.input-row.is-focused { box-shadow: 0 0 0 2px var(--accent); border-color: var(--accent); }
.input-row.is-rejected { animation: shake 520ms cubic-bezier(0.36, 0.07, 0.19, 0.97) 1; border-color: var(--warn); }
.input-row.is-busy { border-color: var(--warn); }
.slots { display: flex; align-items: center; gap: 4px; flex: 1; min-width: 0; overflow: hidden; }
.slot { display: block; width: 20px; height: 24px; flex: none; background: #fff; border: 1px solid rgba(17,18,20,0.35); }
.fold { color: var(--ink); font-size: 12px; flex: none; }
.caret { width: 2px; height: 22px; background: var(--accent); animation: blink 0.9s steps(1) infinite; flex: none; }
.placeholder { color: var(--muted); font-size: 11px; }
.secret-input { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; pointer-events: none; border: 0; }
.clear { position: relative; z-index: 2; padding: 6px 8px; border-left: 1px solid var(--line); font-size: 10px; }
.clear:hover:not(:disabled) { color: var(--warn); }
.focus-underline { position: absolute; left: 0; right: 0; bottom: -1px; height: 2px; background: var(--accent); }
.hint { margin: 7px 0 10px; color: var(--muted); font-size: 10px; min-height: 14px; }
.hint.warn { color: var(--warn-deep); font-weight: 700; }
.submit {
  width: 100%; height: 46px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 14px; background: var(--ink); color: var(--paper);
  font-size: 12px; letter-spacing: 0.18em;
  transition: background-color 300ms ease, color 300ms ease, box-shadow 300ms ease;
}
.submit:hover:not(:disabled) { background: var(--accent); color: #111214; }
.submit.busy { background: var(--warn); color: #111214; box-shadow: 0 0 0 1px var(--warn-deep); }
.submit-arrow { font-size: 18px; }
.progress { height: 3px; margin-top: 6px; background: var(--line-soft); }
.progress i { display: block; height: 100%; background: var(--warn); transition: width 80ms linear; }

/* 降级视图：同色系纸面 + 朴素输入区，警示色提交、荧光焦点轮廓 */
.archive.is-fallback { background: var(--card); backdrop-filter: none; box-shadow: none; }
.archive.is-fallback .bevel,
.archive.is-fallback .hex-pattern,
.archive.is-fallback .ghost-word,
.archive.is-fallback .photo-scan { display: none; }
.archive.is-fallback .submit { background: var(--warn); color: #111214; }
.archive.is-fallback .submit:hover:not(:disabled) { background: var(--warn-deep); }

@media (max-width: 520px) {
  .archive { padding: 16px; }
  .arc-top { grid-template-columns: 92px 1fr; gap: 12px; }
  .photo { height: 108px; }
  .ghost-word { font-size: 96px; }
  .black-name { font-size: 15px; }
}
</style>
