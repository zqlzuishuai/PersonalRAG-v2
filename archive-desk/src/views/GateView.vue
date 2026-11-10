<script setup>
/**
 * views/GateView.vue —— 门禁 / 二次验证
 * 载体配方：主带中央留出准星位、右侧档案面板、四态（常态 / 进行中 / 失败 / 成功）。
 * 主操作全屏唯一：提交四位调阅凭据。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { credentials, org } from '@/data/registry'
import { useSessionStore } from '@/stores/session'
import { useCurtainStore } from '@/stores/curtain'
import { useArchiveStore } from '@/stores/archive'
import { hms } from '@/utils/format'

import SectionLabel from '@/components/primitives/SectionLabel.vue'
import Tag from '@/components/primitives/Tag.vue'
import DotLink from '@/components/primitives/DotLink.vue'
import PrimaryAction from '@/components/primitives/PrimaryAction.vue'
import FieldTable from '@/components/primitives/FieldTable.vue'
import DecodedText from '@/components/primitives/DecodedText.vue'
import LeaderLine from '@/components/primitives/LeaderLine.vue'
import TiltPanel from '@/components/layout/TiltPanel.vue'
import VerifyComplex from '@/components/state/VerifyComplex.vue'
import FailureBlock from '@/components/state/FailureBlock.vue'

const router = useRouter()
const route = useRoute()
const session = useSessionStore()
const curtain = useCurtainStore()
const archive = useArchiveStore()

const code = ref('')
const pct = ref(0)
const focused = ref(false)
const leaving = ref(false)
const inputEl = ref(null)
const openedAt = ref(hms())

const busy = computed(() => session.phase === 'working')
const failing = computed(() => session.phase === 'failure')

const fields = computed(() => [
  { k: 'HOST', v: 'TERMINAL · 02' },
  { k: 'SESSION', v: `0412-${org.code}` },
  { k: 'LOCKED AT', v: openedAt.value },
  { k: 'KEYMAP', v: 'US' },
  { k: 'LEVEL', v: 'A' },
  { k: 'ATTEMPT', v: `${session.attempts} / 3` },
])

const failureLogs = computed(() => [
  'AUTHORIZATION FAILED',
  'CREDENTIAL NOT ON ISSUE BOOK',
  `ATTEMPT LEFT ${session.attempts}`,
  'RETURNING TO ACCESS PORTAL',
])

let timers = []
const wait = (ms) =>
  new Promise((resolve) => {
    const t = setTimeout(resolve, ms)
    timers.push(t)
  })

onBeforeUnmount(() => timers.forEach((t) => clearTimeout(t)))
onMounted(() => {
  archive.seed()

  // 预览用：?demo=working|failure|success 直接进入某一态，便于验收四态
  const demo = route.query.demo
  if (demo === 'failure') {
    session.toFailure('凭据 0000 未登记于签发簿 · 剩余尝试 2 次')
    curtain.flip(1)
  } else if (demo === 'working') {
    session.toWorking()
    pct.value = 6
    requestAnimationFrame(() => {
      pct.value = 92
    })
  } else if (demo === 'success') {
    session.toSuccess('调阅员 · 07')
  }

  // 只允许把光标交给输入框，不自动弹出键盘
  setTimeout(() => inputEl.value && inputEl.value.blur(), 0)
})

function focusInput() {
  if (failing.value) return
  inputEl.value?.focus()
}

function onInput(e) {
  const v = String(e.target.value || '')
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .slice(0, 4)
  code.value = v
  if (e.target.value !== v) e.target.value = v
}

function fill(c) {
  if (failing.value) return
  code.value = c.code
  inputEl.value?.focus()
}

async function submit() {
  if (session.busy || failing.value || code.value.length < 4) return

  const prevCurtain = curtain.value
  const result = session.check(code.value)

  session.toWorking()
  pct.value = 6
  requestAnimationFrame(() => {
    pct.value = 92
  })

  await wait(1400)
  pct.value = 100
  await wait(180)

  if (result.ok) {
    session.toSuccess(result.holder)
    archive.push(`ADMIT ${result.holder} · LEVEL ${result.level}`)
    leaving.value = true
    await wait(520)
    router.push('/console')
    return
  }

  // 失败：整屏翻墨幕 + 中央黑板
  curtain.flip(1)
  session.toFailure(result.reason)
  pct.value = 0
  await wait(2600)
  curtain.flip(prevCurtain)
  session.reset()
  code.value = ''
  await wait(320)
  leaving.value = false
}
</script>

<template>
  <section class="zone zone--a gate__rail" :class="{ 'is-leaving': leaving }">
    <SectionLabel en="ACCESS CONTROL" zh="门禁" />

    <p class="gate__para">
      本厅只接受登记在册的调阅凭据。请将四位口令填入中栏，任何一次失败都会消耗尝试次数。
    </p>

    <div class="gate__block">
      <SectionLabel en="ISSUED" zh="已签发" />
      <div class="gate__creds">
        <DotLink v-for="c in credentials" :key="c.code" :disabled="failing || busy" @click="fill(c)">
          <span class="mono gate__cred-code">{{ c.code }}</span>
          <span class="gate__cred-holder">{{ c.holder }}</span>
        </DotLink>
      </div>
    </div>

    <div class="gate__block">
      <SectionLabel en="SEAL" zh="封条" />
      <div class="gate__seal">
        <span class="lbl">SEAL · 0411</span>
        <span class="lbl">CHECKED 06:58:12</span>
      </div>
      <LeaderLine dir="h" :len="44" label="TO AXIS" class="gate__leader" />
    </div>

    <div class="gate__block">
      <SectionLabel en="LAST ADMITTED" zh="上次入厅" />
      <div class="gate__seal">
        <span class="lbl">14:22:07 · READER 07</span>
        <span class="lbl">RETURNED 16:41:02</span>
      </div>
    </div>

    <div class="gate__rail-foot">
      <span class="lbl">GATE · A-01</span>
      <span class="lbl">{{ org.zh }}</span>
    </div>
  </section>

  <section class="zone zone--b gate__center" :class="{ 'is-leaving': leaving }">
    <div class="gate__stack">
      <SectionLabel en="AUTHORIZATION" zh="授权" :accent="true" />

      <VerifyComplex
        :running="busy"
        :pct="pct"
        :word="session.phase === 'success' ? 'GRANTED' : 'SEALED'"
        :zh="session.phase === 'success' ? '凭据已核验' : '等待凭据'"
      />

      <div class="gate__code" :class="{ 'is-off': busy || failing }">
        <span class="lbl gate__code-label">CLEARANCE CODE · 4</span>

        <div class="slots" :class="{ 'is-focus': focused }" @click="focusInput">
          <div
            v-for="i in 4"
            :key="i"
            class="slot"
            :class="{
              'is-filled': code.length >= i,
              'is-cursor': focused && code.length < 4 && code.length === i - 1,
            }"
          >
            {{ code[i - 1] || '' }}
          </div>
        </div>

        <input
          ref="inputEl"
          class="sr-only"
          type="text"
          inputmode="latin"
          autocomplete="off"
          spellcheck="false"
          maxlength="4"
          aria-label="四位调阅凭据"
          :value="code"
          :disabled="busy || failing"
          @input="onInput"
          @focus="focused = true"
          @blur="focused = false"
          @keydown.enter.prevent="submit"
        />
      </div>

      <div class="gate__action">
        <PrimaryAction
          en="ENTER ARCHIVE"
          zh="进入调阅厅"
          busy-en="VERIFYING"
          busy-zh="核验中"
          :busy="busy"
          :disabled="failing || code.length < 4"
          @click="submit"
        />
        <span class="lbl gate__hint">
          <span class="kbd">ENTER</span> 提交 · 点选左侧凭据可直接填入
        </span>
      </div>

      <p v-if="session.reason && !failing" class="gate__reason">
        <i class="gate__rsq" />
        <span>{{ session.reason }}</span>
      </p>

      <p class="gate__caption">
        <span class="gate__caption-zh">出示授权口令以进入阅览室。</span>
        <span class="lbl">CREDENTIAL REQUIRED · READING ROOM 02</span>
      </p>
    </div>

    <FailureBlock v-if="failing" :reason="session.reason" :logs="failureLogs" />
  </section>

  <section class="zone zone--c" :class="{ 'is-leaving': leaving }">
    <TiltPanel>
      <div class="gp">
        <span class="gp__ghost" aria-hidden="true">GATE</span>

        <div class="gp__head">
          <SectionLabel en="SECTION PROFILE" />
          <Tag>ACCESS</Tag>
        </div>

        <div class="gp__body">
          <h2 class="gp__zh">门禁 · 阅览室 02</h2>
          <DecodedText class="gp__en lbl" text="ACCESS PORTAL · LEVEL A" />

          <div class="gp__row">
            <div class="gp__plate" aria-hidden="true"><span>{{ org.mark }}</span></div>
            <FieldTable class="gp__ft" :items="fields" />
          </div>

          <p class="gp__note">凭据由值守台签发，一人一份；遗失即作废，需重新登记。</p>
        </div>

        <div class="gp__foot">
          <span class="lbl">RECEIVED {{ openedAt }}</span>
          <span class="gp__seal">
            <span class="mono">{{ org.mark }}</span>
          </span>
        </div>
      </div>
    </TiltPanel>
  </section>
</template>

<style scoped>
/* ——— 左栏 ——— */
.gate__rail {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-top: 28px;
  transition: transform var(--d-switch) linear, opacity var(--d-switch) linear;
}

.gate__para {
  font-family: var(--font-sans);
  font-size: var(--t11);
  line-height: 1.7;
  letter-spacing: 0.4px;
  color: var(--dim);
  max-width: 30ch;
}

.gate__block {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.gate__creds {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gate__cred-code {
  letter-spacing: 1.6px;
  color: var(--fg);
}

.gate__cred-holder {
  font-family: var(--font-sans);
  font-size: var(--t95);
  letter-spacing: 1px;
  opacity: 0.75;
}

.gate__seal {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.gate__leader {
  margin-top: 6px;
}

.gate__rail-foot {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

/* ——— 中栏 ——— */
.gate__center {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--d-switch) linear, opacity var(--d-switch) linear;
}

.gate__stack {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  width: 100%;
  max-width: 400px;
}

.gate__code {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  transition: opacity var(--d-micro) linear;
}

.gate__code.is-off {
  opacity: 0.35;
  pointer-events: none;
}

.gate__code-label {
  color: var(--dim);
}

.gate__action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 9px;
  width: 100%;
}

.gate__hint {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--dim);
}

.gate__reason {
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: var(--font-mono);
  font-size: var(--t8);
  letter-spacing: 1.2px;
  color: var(--dim);
  text-align: center;
}

.gate__rsq {
  flex: none;
  width: 5px;
  height: 5px;
  background: var(--alert);
}

.gate__caption {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
}

.gate__caption-zh {
  font-family: var(--font-sans);
  font-size: var(--t125);
  letter-spacing: 2.5px;
  color: var(--fg);
}

/* ——— 右栏档案面板 ——— */
.gp {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.gp__ghost {
  position: absolute;
  right: -14px;
  bottom: -18px;
  font-family: var(--font-sans);
  font-size: var(--t112);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -4px;
  color: var(--fg);
  opacity: 0.06;
  pointer-events: none;
  user-select: none;
}

.gp__head {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 14px;
  border-bottom: 1px solid var(--line);
}

.gp__body {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: 16px 14px 8px;
}

.gp__zh {
  font-family: var(--font-sans);
  font-size: var(--t21);
  font-weight: 600;
  line-height: 1.1;
  letter-spacing: -0.2px;
  color: var(--fg);
}

.gp__en {
  display: block;
  margin-top: 6px;
  color: var(--dim);
}

.gp__row {
  display: flex;
  align-items: stretch;
  gap: 14px;
  margin-top: 18px;
}

.gp__plate {
  position: relative;
  flex: none;
  width: 84px;
  display: grid;
  place-items: center;
  background: #0b0b0c;
  color: #f2f0eb;
  font-size: var(--t30);
  line-height: 1;
}

.gp__ft {
  flex: 1;
  min-width: 0;
  align-content: start;
}

.gp__note {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1.5px solid var(--hair);
  font-family: var(--font-sans);
  font-size: var(--t11);
  line-height: 1.7;
  letter-spacing: 0.4px;
  color: var(--dim);
}

.gp__foot {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-top: 1px solid var(--line);
}

.gp__seal {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid var(--hair);
  font-size: var(--t17);
  color: var(--fg);
}

/* 成功：主面板与辅助区块向边缘抽离 */
.is-leaving.zone--a {
  transform: translateX(-48px);
  opacity: 0;
}

.is-leaving.zone--b {
  transform: translateY(-24px);
  opacity: 0;
}

.is-leaving.zone--c {
  transform: translateX(72px);
  opacity: 0;
}

.zone--c {
  transition: transform var(--d-switch) linear, opacity var(--d-switch) linear;
}

.mode-column .gp__ghost {
  display: none;
}

.mode-column .gate__rail {
  padding-top: 0;
}

.mode-column .gate__para {
  max-width: none;
}
</style>
