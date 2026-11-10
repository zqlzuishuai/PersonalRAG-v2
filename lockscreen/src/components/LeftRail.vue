<script setup>
/**
 * 左索引栏：微文案、命令日志、快捷键图例、章节标题。
 * 关键逻辑：日志由状态机 pushLog 追加，最多保留 7 条；章节序号与步骤点同源。
 */
import { SECTIONS, SHORTCUTS } from '../config'
defineProps({
  logs: { type: Array, required: true },
  activeStep: { type: Number, required: true },
  displayPhase: { type: String, default: 'ready' },
})
</script>

<template>
  <div class="rail">
    <p class="micro muted rail-note">
      ARCHIVE UNIT / 04<br />
      FRAME SEALED · NO OUTPUT<br />
      档案终端 · 无输出
    </p>

    <div class="rail-title mono micro">SECTIONS / 章节</div>
    <ul class="sections">
      <li v-for="(s, i) in SECTIONS" :key="s.no" :class="{ on: i <= activeStep }">
        <span class="mono">{{ s.no }}</span>
        <span class="ellipsis">{{ s.label }}</span>
      </li>
    </ul>

    <div class="rail-title mono micro">COMMAND LOG / 命令日志</div>
    <ul class="logs mono" aria-live="polite">
      <li v-for="(entry, i) in logs" :key="`${entry.t}-${entry.code}-${i}`">
        <span class="t">{{ entry.t }}</span>
        <span class="ellipsis">{{ entry.code }}</span>
      </li>
    </ul>

    <div class="rail-title mono micro">KEY LEGEND / 快捷键</div>
    <ul class="keys">
      <li v-for="k in SHORTCUTS" :key="k.key">
        <kbd class="mono">{{ k.key }}</kbd><span class="mono muted">{{ k.label }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.rail { display: flex; flex-direction: column; gap: 12px; font-size: 12px; }
.rail-note { line-height: 1.9; margin: 0 0 8px; }
.rail-title { border-top: 1px solid var(--line); padding-top: 8px; color: var(--muted); }
.sections, .logs, .keys { list-style: none; margin: 0; padding: 0; }
.sections li { display: flex; gap: 10px; padding: 4px 0; color: var(--muted); }
.sections li.on { color: var(--ink); }
.sections li.on span:first-child { color: var(--accent); }
.logs { font-size: 11px; min-height: 108px; }
.logs li { display: flex; gap: 10px; padding: 3px 0; border-bottom: 1px solid var(--line-soft); }
.logs .t { color: var(--muted); flex: none; }
.logs li:first-child { color: var(--ink); }
.keys { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.keys li { display: flex; align-items: center; gap: 8px; }
kbd { border: 1px solid var(--line); padding: 3px 6px; font-size: 10px; letter-spacing: 0.08em; }
.keys .mono { font-size: 10px; }
</style>
