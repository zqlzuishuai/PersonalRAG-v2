<script setup>
/**
 * 页脚：电源项、声音开关、署名。
 * 关键逻辑：所有电源类操作必须二次确认 —— 首次点击进入待确认态，
 * 3 秒内再次点击同一项才记录执行；点击其它项或超时自动撤销。
 */
import { ref, computed, onBeforeUnmount } from 'vue'
import { POWER_ITEMS, COPY } from '../config'
const props = defineProps({
  machine: { type: Object, required: true },
  capabilities: { type: Object, required: true },
  silent: { type: Boolean, default: false },
})
const pendingId = ref(null)
const notice = ref('')
let timer
const cancelPending = () => { pendingId.value = null; clearTimeout(timer) }

const onPower = (id) => {
  if (pendingId.value !== id) {
    pendingId.value = id
    notice.value = 'CONFIRM REQUIRED / 再次点击以确认'
    clearTimeout(timer)
    timer = setTimeout(() => { pendingId.value = null; notice.value = '' }, 3000)
    return
  }
  cancelPending()
  // 演示环境只记录事实，不执行真实的挂起 / 关机动作。
  props.machine.confirmPower(id)
  notice.value = `${id.toUpperCase()} · CONFIRMED / 演示环境不执行`
  setTimeout(() => { notice.value = '' }, 3200)
}
const soundLabel = computed(() => props.silent ? 'MUTED / 副屏静默' : props.machine.soundOn ? 'SOUND ON' : 'SOUND OFF')
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <footer class="footer">
    <div v-if="capabilities.powerItems" class="power-items" role="group" aria-label="电源操作">
      <span class="foot-label mono micro muted">POWER / 电源</span>
      <button
        v-for="item in POWER_ITEMS"
        :key="item.id"
        type="button"
        class="power mono micro"
        :class="{ pending: pendingId === item.id }"
        :aria-label="`${item.zh}，需二次确认`"
        @click="onPower(item.id)"
      >
        <span class="power-dot"></span>
        {{ pendingId === item.id ? 'CONFIRM ?' : item.label }}
      </button>
    </div>

    <button v-if="capabilities.sound" type="button" class="sound mono micro"
            :disabled="silent" :aria-pressed="machine.soundOn" @click="machine.toggleSound()">
      <span class="sound-bars" aria-hidden="true"><i></i><i></i><i></i></span>
      {{ soundLabel }}
    </button>

    <div class="foot-sign mono micro muted">{{ COPY.signature }}</div>
    <div v-if="notice" class="foot-notice mono micro" role="status">{{ notice }}</div>
  </footer>
</template>

<style scoped>
.footer { display: flex; align-items: center; justify-content: flex-end; gap: 14px; flex-wrap: wrap; position: relative; }
.foot-label { font-size: 9px; }
.power-items { display: flex; align-items: center; gap: 8px; }
.power { display: inline-flex; align-items: center; gap: 6px; padding: 6px 9px; border: 1px solid var(--line); font-size: 10px; letter-spacing: 0.1em; transition: border-color 240ms ease, background-color 240ms ease, color 240ms ease; }
.power:hover { border-color: var(--ink); }
.power.pending { background: var(--warn); border-color: var(--warn); color: #111214; }
.power-dot { width: 6px; height: 6px; background: var(--accent); }
.power.pending .power-dot { background: #111214; animation: pulse 700ms ease-in-out infinite; }
.sound { display: inline-flex; align-items: center; gap: 7px; padding: 6px 9px; border: 1px solid var(--line); font-size: 10px; }
.sound:hover:not(:disabled) { border-color: var(--accent); }
.sound-bars { display: inline-flex; align-items: center; gap: 2px; height: 10px; }
.sound-bars i { width: 2px; height: 100%; background: var(--accent); }
.sound-bars i:nth-child(2) { height: 60%; }
.foot-sign { font-size: 9px; }
.foot-notice { position: absolute; right: 0; top: -22px; color: var(--warn-deep); font-size: 10px; white-space: nowrap; }
@media (max-width: 520px) { .footer { justify-content: flex-start; gap: 8px; } .foot-sign { width: 100%; } }
</style>
