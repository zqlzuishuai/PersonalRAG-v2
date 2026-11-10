<script setup>
/** archive/LogStream.vue —— 日志流：等间隔逐行打印，每行都带时间戳出处 */
defineProps({
  lines: { type: Array, default: () => [] },
})
</script>

<template>
  <div class="ls">
    <div class="ls__head">
      <span class="lbl">LOG STREAM</span>
      <span class="lbl">{{ String(lines.length).padStart(2, '0') }}/06</span>
    </div>
    <div class="ls__rows">
      <div v-for="l in lines" :key="l.id" class="ls__row">
        <span class="ls__t mono">{{ l.t }}</span>
        <span class="ls__x mono">{{ l.text }}</span>
        <i class="ls__sq" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.ls {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding-top: 10px;
  border-top: 1.5px solid var(--hair);
}

.ls__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 2px;
}

.ls__rows {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-height: 0;
}

.ls__row {
  display: flex;
  align-items: center;
  gap: 10px;
  animation: print-in var(--d-micro) steps(2, end) both;
  white-space: nowrap;
}

.ls__t {
  flex: none;
  font-size: var(--t8);
  letter-spacing: 0;
  color: var(--dim);
}

.ls__x {
  flex: 1;
  min-width: 0;
  font-size: var(--t8);
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--fg);
  overflow: hidden;
  text-overflow: ellipsis;
}

.ls__sq {
  flex: none;
  width: 4px;
  height: 4px;
  background: var(--line);
}

.ls__row:last-child .ls__sq {
  background: var(--accent);
}
</style>
