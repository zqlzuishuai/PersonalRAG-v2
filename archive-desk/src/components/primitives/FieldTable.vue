<script setup>
/** primitives/FieldTable.vue —— 档案字段表：3–6 组 dt/dd，等宽数字，行距 6 */
defineProps({
  items: { type: Array, required: true }, // [{ k: 'OBJECT', v: '…' }]
})
</script>

<template>
  <dl class="ft">
    <template v-for="f in items" :key="f.k">
      <dt>{{ f.k }}</dt>
      <dd>{{ f.v }}</dd>
    </template>
  </dl>
</template>
