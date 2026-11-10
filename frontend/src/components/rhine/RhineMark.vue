<script setup>
defineProps({draw:{type:Number,default:1}})
</script>
<template>
  <svg class="rhine-mark" viewBox="0 0 1200 570" fill="none" aria-hidden="true">
    <!-- Fan-drawn mark ported from rhine-lock; see THIRD_PARTY_NOTICES.md. -->
    <path d="M691.70 199.36 431.75 442.13A215 215 0 1 1 431.75 127.87L768.25 442.13A215 215 0 1 0 768.25 127.87" stroke="currentColor" stroke-width="100" stroke-dasharray="2813.06 2813.06" :stroke-dashoffset="2813.06*(1-draw)" />
    <path d="M258 187h64v66h66v64h-66v66h-64v-66h-66v-64h66ZM837 256h162v64H837Z" fill="currentColor" :opacity="Math.max(0,Math.min(1,(draw-.55)/.45))" />
  </svg>
</template>
