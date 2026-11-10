<script setup>
/**
 * primitives/PrimaryAction.vue —— 全屏唯一的主操作
 * 纯黑长条 + 内嵌反白字 + 末端强调色箭头；悬停整条转强调色。
 */
defineProps({
  en: { type: String, required: true },
  zh: { type: String, default: '' },
  busy: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  busyEn: { type: String, default: '' },
  busyZh: { type: String, default: '' },
})
</script>

<template>
  <button
    type="button"
    class="pa"
    :class="{ 'pa--busy': busy }"
    :disabled="disabled || busy"
  >
    <span class="pa__label">
      <span>{{ busy ? busyEn || en : en }}</span>
      <span v-if="busy ? busyZh : zh" class="pa__zh">{{ busy ? busyZh : zh }}</span>
    </span>
    <span class="pa__arrow" aria-hidden="true" />
  </button>
</template>
