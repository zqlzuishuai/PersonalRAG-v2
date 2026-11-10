<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
const now = ref(new Date())
const time = computed(() => now.value.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Hong_Kong' }))
const date = computed(() => now.value.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Hong_Kong' }))
let timer
onMounted(() => { timer = setInterval(() => { now.value = new Date() }, 10000) })
onUnmounted(() => clearInterval(timer))
</script>
<template>
  <div class="rhine-clock" aria-label="香港时间"><time :datetime="now.toISOString()">{{ time }}</time><span>{{ date }} <i>HKT</i></span></div>
</template>
