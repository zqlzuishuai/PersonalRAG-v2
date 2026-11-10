<script setup>
/**
 * 拒绝态黑底橙框警示板：三角标、四条逐行出现的记录、尝试次数。
 * 关键逻辑：仅 rejected 时挂载；两条拒绝原因共用同一版式，只替换事实文案。
 */
defineProps({
  copy: { type: Object, required: true },
  rows: { type: Array, required: true },
  attempts: { type: Number, required: true },
})
</script>

<template>
  <div class="warning" role="alert">
    <div class="warn-head">
      <svg class="tri" viewBox="0 0 32 28" aria-hidden="true">
        <path d="M16 2 L31 26 H1 Z" fill="none" stroke="var(--warn)" stroke-width="2" />
        <path d="M16 10 V18" stroke="var(--warn)" stroke-width="2" />
        <circle cx="16" cy="22" r="1.4" fill="var(--warn)" />
      </svg>
      <div>
        <div class="warn-title display">{{ copy.title }}</div>
        <div class="warn-zh">{{ copy.zh }}</div>
      </div>
    </div>
    <div class="warn-en mono micro muted">{{ copy.en }}</div>
    <ul class="warn-rows mono">
      <li v-for="(row, i) in rows" :key="row" :style="{ animationDelay: `${i * 180}ms` }" class="decode">{{ row }}</li>
    </ul>
    <div class="warn-foot mono micro">
      <span>ATTEMPT {{ String(attempts).padStart(2, '0') }}</span>
      <span>SESSION LOCKED / 会话保持锁定</span>
    </div>
  </div>
</template>

<style scoped>
.warning {
  height: 100%; padding: 18px 20px;
  background: #0b0c0e; color: #f2f0ec;
  border: 2px solid var(--warn);
  box-shadow: 0 0 0 6px #0b0c0e, 0 0 0 8px var(--warn), 0 24px 60px rgba(0, 0, 0, 0.6);
}
.warn-head { display: flex; gap: 14px; align-items: flex-start; }
.tri { width: 32px; height: 28px; flex: none; margin-top: 2px; }
.warn-title { font-size: 22px; color: var(--warn); letter-spacing: 0.02em; }
.warn-zh { font-size: 13px; margin-top: 6px; }
.warn-en { margin: 10px 0 12px; font-size: 10px; letter-spacing: 0.12em; }
.warn-rows { list-style: none; margin: 0; padding: 0; border-top: 1px solid rgba(255,255,255,0.16); }
.warn-rows li { padding: 6px 0; font-size: 11px; letter-spacing: 0.08em; border-bottom: 1px solid rgba(255,255,255,0.1); }
.warn-foot { display: flex; justify-content: space-between; gap: 10px; margin-top: 12px; color: var(--warn); font-size: 10px; }
</style>
