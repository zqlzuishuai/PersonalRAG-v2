<script setup>
/**
 * views/SpecView.vue —— 形式规范
 * 把风格层本身当成一份档案来陈列：幕值、色值、字号阶梯、三种组件形态、四态、动效、验收。
 * 本页唯一的主操作是翻幕 —— 全屏仍然只有一个主操作。
 */
import { computed } from 'vue'

import { useCurtainStore } from '@/stores/curtain'
import { useSessionStore } from '@/stores/session'
import { stages } from '@/data/registry'

import SectionLabel from '@/components/primitives/SectionLabel.vue'
import Tag from '@/components/primitives/Tag.vue'
import DotLink from '@/components/primitives/DotLink.vue'
import PrimaryAction from '@/components/primitives/PrimaryAction.vue'

const curtain = useCurtainStore()
const session = useSessionStore()

const ROLES = [
  { k: 'BG', p: '#E7E5E1', i: '#0B0B0C' },
  { k: 'FG', p: '#111214', i: '#F2F0EB' },
  { k: 'CARD', p: '#F6F5F2', i: '#151618' },
  { k: 'TAB', p: '#E2E0DC', i: '#1D1E20' },
  { k: 'DIM', p: '#8B8882', i: '#6F6D68' },
  { k: 'LINE', p: '#C9C6C0', i: '#2B2B2D' },
]

const LADDER = [
  { px: '92', t: 'HUGE 巨字' },
  { px: '46', t: 'DISPLAY 编号' },
  { px: '30', t: 'TITLE 标题' },
  { px: '21', t: 'HEAD 小标题' },
  { px: '17', t: 'LEAD 引文' },
  { px: '15', t: 'BODY 正文' },
  { px: '12.5', t: 'TEXT 说明' },
  { px: '11', t: 'CAPTION 注释' },
  { px: '9.5', t: 'LABEL 标签' },
  { px: '8', t: 'MICRO 微文案' },
]

const STATES = [
  { n: 'STANDBY', zh: '常态', d: '标记块在基准位；状态带显示阶段名与可执行操作；主操作可点。' },
  { n: 'AUTHORIZING', zh: '进行中', d: '三组细弧自转 + 双线框进度条；主操作转强调色并改为进行中文案；字段只读。' },
  { n: 'DENIED', zh: '失败', d: '整屏翻墨幕；中央 420×260 纯黑板；4 行日志逐条打印；2.6s 后回常态并留一行原因。' },
  { n: 'GRANTED', zh: '成功', d: '进度补满；主面板与辅助区块向边缘抽离；进入下一屏。' },
]

const MOTION = [
  { k: 'MICRO', d: '140–320ms', u: '悬停、焦点、逐字解码的节拍' },
  { k: 'SWITCH', d: '400–600ms', u: '阶段切换、面板抽离、空闲滑出' },
  { k: 'FLOW', d: '1.2–1.6s', u: '一次完整核验流程' },
  { k: 'HOLD', d: '2.6s / 3.6s', u: '倒计时与失败自动回退（全站统一）' },
]

const AUDIT = [
  '灰度截图仍能读出「巨字—标签—微文案」三级层级',
  '缩放到 50%，品牌锁排、主操作、当前阶段仍可辨认',
  '彩色面积 ≤5%，且只有强调色与警示色两个色相',
  '字号全部来自 10 级阶梯，无自创中间值',
  '每个控件属于三种形态之一，主操作全屏唯一',
  '文案长度 ×3 后不溢出、不破版、不缩字',
  '所有交互具备 hover 与键盘焦点两态，焦点为 2px 强调色外框',
  '四态相邻之间至少 3 处可见差异',
  '关闭一切插图与背景之后，界面仍能成立',
  '无圆角、无多层投影、无图标库图形、无 emoji、无感叹号',
]

const pct = computed(() => Math.round(curtain.value * 100))

function onSlide(e) {
  curtain.apply(Number(e.target.value) / 100)
}
</script>

<template>
  <section class="zone zone--a sp__a">
    <SectionLabel en="CURTAIN VALUE" zh="幕值" />

    <p class="sp__para">两幕是同一套角色的两组取值，由一条 0→1 的幕值整体插值。翻幕必须单帧完成。</p>

    <div class="sp__slider">
      <input
        class="slider"
        type="range"
        min="0"
        max="100"
        step="1"
        :value="pct"
        aria-label="幕值"
        @input="onSlide"
      />
      <div class="sp__slider-row">
        <span class="lbl">{{ curtain.value.toFixed(2) }}</span>
        <span class="lbl">{{ curtain.isInk ? 'INK' : 'PAPER' }}</span>
      </div>
    </div>

    <div class="sp__ops">
      <DotLink :current="!curtain.isInk" @click="curtain.flip(0)">PAPER</DotLink>
      <DotLink :current="curtain.isInk" @click="curtain.flip(1)">INK</DotLink>
    </div>

    <div class="sp__block">
      <SectionLabel en="ROLES" zh="六档" />
      <table class="sp__roles">
        <thead>
          <tr>
            <th>ROLE</th>
            <th>PAPER</th>
            <th>INK</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in ROLES" :key="r.k">
            <td class="mono">{{ r.k }}</td>
            <td class="mono">{{ r.p }}</td>
            <td class="mono">{{ r.i }}</td>
          </tr>
        </tbody>
      </table>
      <div class="sp__chips">
        <span class="sp__chips-row">
          <span class="sp__chip" style="background: #b9e432" />
          <span class="lbl">ACCENT · #B9E432</span>
        </span>
        <span class="sp__chips-row">
          <span class="sp__chip" style="background: #ff7b00" />
          <span class="lbl">ALERT · #FF7B00</span>
        </span>
      </div>
    </div>

    <div class="sp__block">
      <SectionLabel en="STAGE STOP" zh="阶段跳位" />
      <div class="sp__ops">
        <DotLink
          v-for="(s, i) in stages"
          :key="s.n"
          :current="session.stage === i"
          @click="session.setStage(i)"
        >
          {{ s.n }} {{ s.en }}
        </DotLink>
      </div>
    </div>
  </section>

  <section class="zone zone--b sp__b">
    <div class="sp__head">
      <SectionLabel en="TYPE LADDER" zh="字号阶梯" />
      <span class="lbl">10 STEPS · 8 / 112</span>
    </div>

    <div class="sp__ladder">
      <div v-for="l in LADDER" :key="l.px" class="sp__row">
        <span class="sp__px mono">{{ l.px }}</span>
        <span class="sp__sample" :style="{ fontSize: `var(--t${l.px.replace('.', '')})` }">
          {{ l.t }}
        </span>
      </div>
    </div>

    <div class="sp__head sp__head--mt">
      <SectionLabel en="FONT PAIR" zh="两族" />
      <span class="lbl">GEOMETRIC / MONO</span>
    </div>

    <div class="sp__pair">
      <div class="sp__pair-row">
        <span class="sp__pair-k lbl">SANS</span>
        <span class="sp__pair-v sans">Montserrat · 标题与巨字 · 负字距</span>
      </div>
      <div class="sp__pair-row">
        <span class="sp__pair-k lbl">MONO</span>
        <span class="sp__pair-v mono">JetBrains Mono · 标签编号时间戳</span>
      </div>
    </div>

    <div class="sp__head sp__head--mt">
      <SectionLabel en="FORMS" zh="三种形态" />
      <span class="lbl">ONLY THREE</span>
    </div>

    <div class="sp__forms">
      <div class="sp__form">
        <span class="lbl">01</span>
        <Tag>SOLID BLOCK</Tag>
        <span class="lbl">实心块标签</span>
      </div>
      <div class="sp__form">
        <span class="lbl">02</span>
        <Tag variant="outline">OUTLINE BLOCK</Tag>
        <span class="lbl">描边块</span>
      </div>
      <div class="sp__form">
        <span class="lbl">03</span>
        <DotLink>DOT + TEXT</DotLink>
        <span class="lbl">纯文字 + 方点</span>
      </div>
    </div>

    <div class="sp__table">
      <div class="sp__table-note">
        <span class="lbl">TABLE</span>
        <span class="sp__note-zh">无斑马纹、无竖线，仅表头下一条 1.5px 横线；悬停整行转墨底反白。</span>
      </div>
    </div>
  </section>

  <section class="zone zone--c sp__c">
    <div class="sp__head">
      <SectionLabel en="FOUR STATES" zh="四态" />
      <span class="lbl">MIN. 3 DIFFS</span>
    </div>

    <ul class="sp__states">
      <li v-for="s in STATES" :key="s.n" class="sp__state">
        <div class="sp__state-top">
          <Tag :variant="s.n === 'DENIED' ? 'alert' : s.n === 'AUTHORIZING' ? 'accent' : 'solid'">
            {{ s.n }}
          </Tag>
          <span class="lbl">{{ s.zh }}</span>
        </div>
        <p class="sp__state-d">{{ s.d }}</p>
      </li>
    </ul>

    <div class="sp__head sp__head--mt">
      <SectionLabel en="MOTION" zh="动效" />
      <span class="lbl">STEPS, NOT SPRINGS</span>
    </div>

    <ul class="sp__motion">
      <li v-for="m in MOTION" :key="m.k" class="sp__motion-row">
        <span class="sp__motion-k mono">{{ m.k }}</span>
        <span class="sp__motion-d mono">{{ m.d }}</span>
        <span class="sp__motion-u">{{ m.u }}</span>
      </li>
    </ul>

    <div class="sp__action">
      <PrimaryAction en="FLIP CURTAIN" zh="翻幕" @click="curtain.toggle()" />
    </div>

    <div class="sp__head sp__head--mt">
      <SectionLabel en="AUDIT" zh="验收" />
      <span class="lbl">10 / 10</span>
    </div>

    <ol class="sp__audit">
      <li v-for="(a, i) in AUDIT" :key="a" class="sp__audit-row">
        <span class="sp__audit-n mono">{{ String(i + 1).padStart(2, '0') }}</span>
        <span class="sp__audit-t">{{ a }}</span>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.sp__a {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-top: 14px;
}

.sp__para {
  font-family: var(--font-sans);
  font-size: var(--t11);
  line-height: 1.7;
  letter-spacing: 0.4px;
  color: var(--dim);
}

.sp__slider {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 14px;
  background: transparent;
  cursor: pointer;
}

.slider::-webkit-slider-runnable-track {
  height: 1px;
  background: var(--hair);
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 10px;
  height: 14px;
  margin-top: -6.5px;
  background: var(--blk);
  border: 0;
  border-radius: 0;
}

.slider::-moz-range-track {
  height: 1px;
  background: var(--hair);
}

.slider::-moz-range-thumb {
  width: 10px;
  height: 14px;
  background: var(--blk);
  border: 0;
  border-radius: 0;
}

.sp__slider-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sp__ops {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}

.sp__block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sp__roles {
  width: 100%;
  border-collapse: collapse;
}

.sp__roles th {
  padding: 3px 0;
  background: transparent;
  color: var(--dim);
  font-family: var(--font-mono);
  font-size: var(--t8);
  font-weight: 400;
  letter-spacing: 1.2px;
  text-align: left;
}

.sp__roles tr {
  border-bottom: 1px solid var(--line);
}

.sp__roles td {
  padding: 4px 0;
  font-size: var(--t95);
  color: var(--fg);
}

.sp__chips {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sp__chips-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sp__chip {
  width: 10px;
  height: 10px;
  flex: none;
}

/* ——— 中栏 ——— */
.sp__b,
.sp__c {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  overflow: auto;
  padding-top: 14px;
  padding-bottom: 8px;
}

.sp__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex: none;
}

.sp__head--mt {
  margin-top: 10px;
}

.sp__ladder {
  display: flex;
  flex-direction: column;
  border-top: 1.5px solid var(--hair);
}

.sp__row {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding: 3px 0;
  border-bottom: 1px solid var(--line);
  overflow: hidden;
}

.sp__px {
  flex: none;
  width: 34px;
  font-size: var(--t8);
  color: var(--dim);
}

.sp__sample {
  font-family: var(--font-sans);
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--fg);
  white-space: nowrap;
}

.sp__pair {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sp__pair-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.sp__pair-k {
  flex: none;
  width: 34px;
}

.sp__pair-v {
  font-size: var(--t125);
  color: var(--fg);
}

.sp__forms {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  padding: 12px 0;
  border-top: 1.5px solid var(--hair);
  border-bottom: 1px solid var(--line);
}

.sp__form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.sp__table {
  margin-top: 4px;
}

.sp__table-note {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding-top: 10px;
  border-top: 1.5px solid var(--hair);
}

.sp__note-zh {
  font-family: var(--font-sans);
  font-size: var(--t95);
  line-height: 1.6;
  color: var(--dim);
}

/* ——— 右栏 ——— */
.sp__states {
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-top: 1.5px solid var(--hair);
  padding-top: 12px;
}

.sp__state {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sp__state-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sp__state-d {
  font-family: var(--font-sans);
  font-size: var(--t11);
  line-height: 1.65;
  letter-spacing: 0.3px;
  color: var(--dim);
}

.sp__motion {
  display: flex;
  flex-direction: column;
  border-top: 1.5px solid var(--hair);
}

.sp__motion-row {
  display: grid;
  grid-template-columns: 74px 92px minmax(0, 1fr);
  gap: 10px;
  align-items: baseline;
  padding: 5px 0;
  border-bottom: 1px solid var(--line);
}

.sp__motion-k {
  font-size: var(--t8);
  letter-spacing: 1.2px;
  color: var(--fg);
}

.sp__motion-d {
  font-size: var(--t8);
  color: var(--accent);
}

.sp__motion-u {
  font-family: var(--font-sans);
  font-size: var(--t95);
  color: var(--dim);
}

.sp__action {
  width: 100%;
  margin: 4px 0 6px;
}

.sp__audit {
  display: flex;
  flex-direction: column;
  gap: 7px;
  border-top: 1.5px solid var(--hair);
  padding-top: 10px;
}

.sp__audit-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.sp__audit-n {
  flex: none;
  font-size: var(--t8);
  color: var(--dim);
}

.sp__audit-t {
  font-family: var(--font-sans);
  font-size: var(--t95);
  line-height: 1.6;
  letter-spacing: 0.3px;
  color: var(--fg);
}

.mode-column .sp__b,
.mode-column .sp__c {
  overflow: visible;
}

.mode-column .sp__forms {
  grid-template-columns: 1fr;
}
</style>
