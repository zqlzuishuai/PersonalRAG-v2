<script setup>
import RhineDecodeText from './RhineDecodeText.vue'
defineProps({motion:{type:Object,required:true},phase:String,anchor:{type:Object,required:true},attempt:{type:Number,default:0},replay:{type:Number,default:0}})
const arc=(r,a,sweep)=>{const p=t=>`${200+r*Math.cos(t*Math.PI/180)} ${200+r*Math.sin(t*Math.PI/180)}`;return`M ${p(a)} A ${r} ${r} 0 ${sweep>180?1:0} 1 ${p(a+sweep)}`}
</script>
<template>
  <div class="rhine-reticle-anchor" :style="{left:anchor.x+'px',top:anchor.y+'px'}" aria-hidden="true">
    <div v-if="motion.verify>.001" class="rhine-auth-ring" :style="{opacity:motion.verify,transform:`translate(-50%,-50%) scale(${.92+.08*motion.verify})`}">
      <div class="ring-halo"></div>
      <svg viewBox="0 0 400 400"><g class="r1"><path :d="arc(150,-60,300)"/></g><g class="r2"><path :d="arc(118,200,70)"/></g><g class="r3"><path :d="arc(52,10,120)"/><path :d="arc(52,190,120)"/></g><g class="o1"><circle cx="350" cy="200" r="4.5"/><circle cx="50" cy="200" r="3"/></g><g class="o2"><circle cx="200" cy="108" r="3.5"/></g></svg>
      <div class="ring-label"><RhineDecodeText :text="phase==='granted'?'PERMISSION AUTHORIZED':'VERIFYING IDENTITY'"/></div>
      <div class="ring-processing"><span>PROCESSING</span><div><i :style="{width:motion.progress*100+'%'}"></i></div></div>
    </div>
    <div v-if="motion.denied>.001" :key="replay" class="rhine-warning" :style="{opacity:Math.min(1,motion.denied*1.4)}">
      <svg class="warning-triangle" viewBox="0 0 30 27"><path d="M15 1L29 26H1Z"/><path d="M15 9V18M15 21V23"/></svg>
      <strong><i></i><RhineDecodeText text="WARNING" :replay="replay"/><i></i></strong>
      <p v-for="(text,i) in ['AUTHENTICATION NOT CONFIRMED','CHECK ACCOUNT AND AUTHORIZATION KEY','ATTEMPT '+String(attempt).padStart(2,'0'),'RETURN TO ACCESS PORTAL']" :key="i" :style="{animationDelay:260+i*240+'ms'}">{{text}}<b></b></p>
    </div>
  </div>
</template>
