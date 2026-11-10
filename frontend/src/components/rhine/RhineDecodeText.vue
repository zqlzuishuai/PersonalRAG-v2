<script setup>
import {onMounted,onUnmounted,ref,watch} from 'vue'
import {decodeFrame} from './decodeText.js'
const props=defineProps({text:{type:String,default:''},duration:Number,replay:{type:Number,default:0}})
const shown=ref(''),tail=ref('')
const preference=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')
let raf=0
function finish(){cancelAnimationFrame(raf);raf=0;shown.value=props.text;tail.value=''}
function start(){
  cancelAnimationFrame(raf)
  if(preference?.matches || globalThis.document?.hidden){finish();return}
  const t0=performance.now();shown.value='';tail.value=''
  const step=now=>{const value=decodeFrame(props.text,now-t0,props.duration);shown.value=value.solid;tail.value=value.tail;if(!value.done)raf=requestAnimationFrame(step);else raf=0}
  raf=requestAnimationFrame(step)
}
watch(()=>[props.text,props.replay],start,{immediate:true})
function visibility(){if(document.hidden)finish()}
function reduced(){if(preference.matches)finish()}
onMounted(()=>{document.addEventListener('visibilitychange',visibility);preference?.addEventListener?.('change',reduced)})
onUnmounted(()=>{cancelAnimationFrame(raf);document.removeEventListener('visibilitychange',visibility);preference?.removeEventListener?.('change',reduced)})
</script>
<template><span class="decode-text"><span class="decode-reserve" aria-hidden="true">{{text}}</span><span class="decode-live" aria-hidden="true">{{shown}}<span class="decode-tail">{{tail}}</span></span><span class="sr-only">{{text}}</span></span></template>
