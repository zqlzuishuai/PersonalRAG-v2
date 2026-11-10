<script setup>
import { onMounted,onUnmounted,ref,watch } from 'vue'
import { follow,isCompact } from './motionMath.js'
const props=defineProps({phase:{type:String,default:'ready'},paused:Boolean,motion:{type:Object,required:true},pointer:{type:Object,default:()=>({x:.5,y:.5})}})
const emit=defineEmits(['frame','anchor'])
const canvas=ref(null),available=ref(false),reduced=ref(false)
let stage,media,observer,disposed=false,starting=false,fallbackRaf=0,last=0
const fins=Array.from({length:90},(_,i)=>{const t=i/90*Math.PI*2;return{x:300+235*Math.cos(t),y:175+210*Math.sin(t)*Math.cos(t),angle:Math.atan2(210*Math.cos(2*t),-235*Math.sin(t))*180/Math.PI}})
function fallback(){
  if(fallbackRaf||document.hidden)return
  last=performance.now()
  const tick=now=>{fallbackRaf=0;if(disposed||document.hidden)return;emit('frame',Math.min(.05,(now-last)/1000),true);last=now;fallbackRaf=requestAnimationFrame(tick)}
  fallbackRaf=requestAnimationFrame(tick)
}
function stopFallback(){cancelAnimationFrame(fallbackRaf);fallbackRaf=0}
function playback(){
  if(document.hidden){stage?.stop();stopFallback();return}
  if(!stage || (props.paused&&props.motion.ready&&props.phase==='ready')){stage?.stop();fallback()}
  else{stopFallback();stage.start()}
}
async function init(){
  if(disposed||starting||stage||reduced.value)return
  starting=true
  try{
    const {Stage}=await import('./scene/Stage.ts')
    if(disposed||reduced.value)return
    const compact=isCompact(innerWidth,innerHeight)||window.matchMedia('(pointer: coarse)').matches
    stage=new Stage(canvas.value,compact?'low':'high')
    if(compact){stage.renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.25));stage.resize()}
    stage.sculptureOffset=-10
    if(props.motion.ready)stage.setAssembled();else stage.hideBand()
    stage.onFrame=dt=>{
      emit('frame',dt,stage.stats.frames>=4)
      const m=props.motion
      stage.maxFps=compact?30:!m.ready||m.exiting||props.phase==='verifying'?0:30
      Object.assign(stage.targets,{verify:m.verify,denied:m.denied,glitch:m.glitch,cardsReveal:m.reveal*(1-m.exitUi)})
      stage.targets.parallaxX=follow(stage.targets.parallaxX,(props.pointer.x-.5)*2,3,dt)
      stage.targets.parallaxY=follow(stage.targets.parallaxY,(props.pointer.y-.5)*2,3,dt)
      const p1=stage.project(.225),p2=stage.project(.275),q1=stage.project(.725),q2=stage.project(.775)
      const rx=p2.x-p1.x,ry=p2.y-p1.y,sx=q2.x-q1.x,sy=q2.y-q1.y,den=rx*sy-ry*sx
      if(Math.abs(den)>1e-3){const a=((q1.x-p1.x)*sy-(q1.y-p1.y)*sx)/den;emit('anchor',{x:p1.x+rx*a,y:p1.y+ry*a,a:stage.project(.65),b:stage.project(.36)})}
    }
    observer=new ResizeObserver(()=>stage?.resize());observer.observe(canvas.value)
    available.value=true;playback()
  }catch{stage?.dispose();stage=null;available.value=false;fallback()}
  finally{starting=false}
}
function preference(){
  reduced.value=media.matches
  if(reduced.value){stage?.dispose();stage=null;observer?.disconnect();available.value=false;emit('anchor',null);fallback()}
  else init()
}
function contextLost(event){event.preventDefault();observer?.disconnect();stage?.dispose();stage=null;available.value=false;emit('anchor',null);fallback()}
watch(()=>[props.paused,props.phase,props.motion.ready],playback)
onMounted(()=>{media=window.matchMedia('(prefers-reduced-motion: reduce)');preference();media.addEventListener('change',preference);document.addEventListener('visibilitychange',playback)})
onUnmounted(()=>{disposed=true;stopFallback();observer?.disconnect();media?.removeEventListener('change',preference);document.removeEventListener('visibilitychange',playback);stage?.dispose()})
defineExpose({playAssemble:(...args)=>stage?.playAssemble(...args),playDissolve:(...args)=>stage?.playDissolve(...args),resetDissolve:()=>stage?.resetDissolve()})
</script>
<template>
  <div class="rhine-scene" aria-hidden="true">
    <svg v-if="!available" class="scene-fallback" viewBox="0 0 600 350"><rect v-for="(fin,i) in fins" :key="i" :x="fin.x-25" :y="fin.y-2" width="50" height="4" :transform="`rotate(${fin.angle} ${fin.x} ${fin.y})`" /></svg>
    <canvas ref="canvas" v-show="available" @webglcontextlost="contextLost"></canvas>
  </div>
</template>
