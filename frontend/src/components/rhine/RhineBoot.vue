<script setup>
import RhineMark from './RhineMark.vue'
import RhineDecodeText from './RhineDecodeText.vue'
defineProps({motion:{type:Object,required:true}})
</script>
<template>
  <div v-if="motion.fade>.001" class="rhine-boot" aria-hidden="true">
    <div class="boot-access" :style="{opacity:1-motion.shift}"><RhineDecodeText text="PERSONAL ARCHIVE · ACCESS PERMISSION REQUIRED"/></div>
    <div class="boot-lockup" :style="{opacity:motion.fade,transform:`translate(calc(-50% - ${motion.shift*150}px), -50%) scale(${1+motion.zoom*.9})`}">
      <RhineMark :draw="motion.draw"/><span>PERSONAL RAG</span>
      <div v-if="motion.shift>.02" class="boot-lines" :style="{opacity:motion.shift}"><RhineDecodeText text="■ KNOWLEDGE ARCHIVE"/><RhineDecodeText text="■ AUTHORIZATION REQUIRED"/></div>
    </div>
  </div>
</template>
