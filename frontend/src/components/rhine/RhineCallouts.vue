<script setup>
defineProps({points:{type:Object,required:true},motion:{type:Object,required:true},scale:{type:Number,default:1}})
</script>
<template>
  <div v-if="points.a&&points.b&&motion.calloutReveal>.01" class="rhine-callouts" :style="{opacity:motion.calloutReveal}" aria-hidden="true">
    <svg><line :x1="points.a.x" :y1="points.a.y" :x2="points.a.x+(732*scale-points.a.x)*motion.calloutReveal" :y2="points.a.y+(126*scale-points.a.y)*motion.calloutReveal"/><line :x1="points.b.x" :y1="points.b.y" :x2="points.b.x+(710*scale-points.b.x)*motion.calloutReveal" :y2="points.b.y+(882*scale-points.b.y)*motion.calloutReveal"/><circle :cx="points.a.x" :cy="points.a.y" :r="3.5*scale"/><circle :cx="points.b.x" :cy="points.b.y" :r="3.5*scale"/></svg>
    <div class="callout-label" :style="{left:742*scale+'px',top:96*scale+'px',transform:`scale(${scale})`}"><small>ARCHIVE SECTION</small><b>KNOWLEDGE NODE</b><span>PERSONAL INFORMATION ARCHIVE</span></div>
    <div class="callout-label" :style="{left:720*scale+'px',top:852*scale+'px',transform:`scale(${scale})`}"><small>ARCHIVE SECTION</small><b>CONNECTED RECORDS</b><span>COLLECT / ORGANIZE / RETRIEVE</span></div>
    <div class="callout-crossing" :style="{left:points.x-34*scale+'px',top:points.y-12*scale+'px',width:300*motion.calloutReveal+'px',transform:`scale(${scale})`}"><b>PERSONAL RAG</b><i></i></div>
  </div>
</template>
