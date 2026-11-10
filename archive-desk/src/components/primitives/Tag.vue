<script setup>
/** primitives/Tag.vue —— 形态 1 实心块 / 形态 2 描边块，二选一，不存在第三种 */
defineProps({
  variant: { type: String, default: 'solid' }, // solid | outline | alert | accent
  as: { type: String, default: 'span' },
})
</script>

<template>
  <component
    :is="as"
    class="tag"
    :class="{
      'tag--outline': variant === 'outline',
      'tag--alert': variant === 'alert',
      'tag--accent': variant === 'accent',
    }"
  >
    <slot />
  </component>
</template>
