<script setup>
/** primitives/SectionLabel.vue —— 小节标签：一条实心短横 + 拉大字距的拉丁标签 */
import DecodedText from './DecodedText.vue'

defineProps({
  en: { type: String, required: true },
  zh: { type: String, default: '' },
  accent: { type: Boolean, default: false },
})
</script>

<template>
  <div class="sl">
    <i class="sl__dash" :class="{ 'is-accent': accent }" />
    <DecodedText :text="en" class="lbl" />
    <span v-if="zh" class="sl__zh">{{ zh }}</span>
  </div>
</template>

<style scoped>
.sl {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.sl__dash {
  flex: none;
  width: 14px;
  height: 2px;
  background: var(--blk);
}

.sl__dash.is-accent {
  background: var(--accent);
}

.sl__zh {
  font-family: var(--font-sans);
  font-size: var(--t95);
  line-height: 1;
  letter-spacing: 1px;
  color: var(--dim);
  white-space: nowrap;
}
</style>
