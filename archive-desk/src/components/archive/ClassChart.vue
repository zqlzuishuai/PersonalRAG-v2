<script setup>
/**
 * archive/ClassChart.vue —— 图表规则：墨色单色系 + 强调色高亮 1 个系列；
 * 仅横向 1px 极弱网格线；无图例边框，标签直接贴线；坐标轴无刻度线只有等宽数字。
 */
import { computed } from 'vue'
import { classes } from '@/data/registry'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  highlight: { type: String, default: '' },
})

const series = computed(() => {
  const list = classes
    .filter((c) => c.key !== 'ALL')
    .map((c) => ({
      key: c.key,
      en: c.en,
      n: props.rows.filter((r) => r.cls === c.key).length,
    }))
  const max = Math.max(1, ...list.map((s) => s.n))
  return list.map((s) => ({
    ...s,
    pct: (s.n / max) * 100,
    hi: s.key === props.highlight,
  }))
})
</script>

<template>
  <div class="cc">
    <div class="cc__head">
      <span class="lbl">ACCESSION BY CLASS</span>
      <span class="lbl">N = {{ rows.length }}</span>
    </div>

    <div class="cc__plot">
      <div v-for="s in series" :key="s.key" class="cc__row">
        <span class="cc__k">{{ s.en }}</span>
        <span class="cc__track">
          <span class="cc__bar" :class="{ 'is-hi': s.hi }" :style="{ width: `${s.pct}%` }" />
        </span>
        <span class="cc__v mono">{{ s.n }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cc {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: none;
}

.cc__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.cc__plot {
  display: flex;
  flex-direction: column;
}

.cc__row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) 22px;
  align-items: center;
  gap: 10px;
  height: 20px;
  border-bottom: 1px solid var(--line);
}

.cc__k {
  font-family: var(--font-mono);
  font-size: var(--t8);
  letter-spacing: 1.2px;
  color: var(--dim);
  white-space: nowrap;
}

.cc__track {
  display: block;
  height: 3px;
  background: transparent;
}

.cc__bar {
  display: block;
  height: 3px;
  background: var(--fg);
  transition: width var(--d-switch) linear;
}

.cc__bar.is-hi {
  background: var(--accent);
}

.cc__v {
  font-size: var(--t95);
  color: var(--fg);
  text-align: right;
}
</style>
