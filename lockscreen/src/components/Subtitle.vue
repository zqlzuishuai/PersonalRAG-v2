<script setup>
/**
 * 双语字幕：中文在上、英文在下，随状态同步切换。
 * 关键逻辑：以 displayPhase 作为 key 触发重挂载，中文逐字解码式出现；
 * 英文同义对应，整行淡入。拒绝态文案由状态机按原因覆盖。
 */
import { computed } from 'vue'
const props = defineProps({
  subtitle: { type: Object, required: true },
  phase: { type: String, required: true },
})
const zhChars = computed(() => [...(props.subtitle.zh || '')])
</script>

<template>
  <div class="subtitle" :key="phase" role="status" aria-live="polite">
    <div class="zh">
      <span
        v-for="(ch, i) in zhChars"
        :key="i"
        class="decode"
        :style="{ animationDelay: `${i * 26}ms` }"
      >{{ ch }}</span>
    </div>
    <div class="en mono micro muted decode" style="animation-delay: 180ms">
      {{ subtitle.en }}
    </div>
  </div>
</template>

<style scoped>
.subtitle { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.zh { font-size: 20px; letter-spacing: 0.08em; }
.en { letter-spacing: 0.22em; }
@media (max-width: 520px) { .zh { font-size: 15px; } .en { font-size: 10px; letter-spacing: 0.1em; } }
</style>
