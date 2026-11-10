<script setup>
/** primitives/DotLink.vue —— 形态 3：纯文字 + 前置方点，用于操作 / 导航 / 图例 */
defineProps({
  to: { type: [String, Object], default: null },
  current: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  size: { type: String, default: 'sm' }, // sm(8) | md(9.5)
})
</script>

<template>
  <RouterLink
    v-if="to && !disabled"
    :to="to"
    class="dotlink"
    :class="[{ 'is-current': current }, { 'dotlink--9': size === 'md' }]"
  >
    <slot />
  </RouterLink>

  <button
    v-else
    type="button"
    class="dotlink"
    :class="[{ 'is-current': current }, { 'is-disabled': disabled }, { 'dotlink--9': size === 'md' }]"
    :aria-pressed="current ? 'true' : undefined"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>
