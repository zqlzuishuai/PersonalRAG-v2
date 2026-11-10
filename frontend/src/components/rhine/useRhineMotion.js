import { reactive } from 'vue'
import { clamp01, entryFrame, follow } from './motionMath.js'

export function useRhineMotion(phase,scene) {
  const preference=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')
  const reduced=preference?.matches ?? false
  const motion=reactive({...entryFrame(reduced?1500:0),exitUi:0,tileReveal:reduced?1:0,verify:0,denied:0,progress:0,glitch:0,calloutReveal:0,exiting:false})
  let elapsed=reduced?1500:0, assembleStarted=reduced, dissolveStarted=false, lastPhase='ready', tear=0
  function effects(dt) {
    const ph=phase.value
    if(ph==='denied' && lastPhase!=='denied')tear=.18
    lastPhase=ph;tear=Math.max(0,tear-dt)
    motion.verify=follow(motion.verify,ph==='verifying'||ph==='granted'?1:0,6,dt)*(1-motion.exitUi)
    motion.denied=follow(motion.denied,ph==='denied'?1:0,28,dt)
    motion.progress=ph==='granted'?follow(motion.progress,1,10,dt):ph==='verifying'?follow(motion.progress,.92,1.4,dt):0
    motion.glitch=tear>0?.8:follow(motion.glitch,0,14,dt)
    const calloutTarget=motion.reveal>=.99&&ph==='ready'?1:0
    motion.calloutReveal=preference?.matches?calloutTarget:follow(motion.calloutReveal,calloutTarget,ph==='granted'?14:5,dt)
  }
  function frame(dt,gpuReady=true) {
    if(!gpuReady || motion.exiting)return
    if(preference?.matches && elapsed<1500){elapsed=1500;Object.assign(motion,entryFrame(1500));motion.tileReveal=1}
    if(elapsed<1500){
      elapsed=Math.min(1500,elapsed+dt*1000)
      Object.assign(motion,entryFrame(elapsed))
      motion.tileReveal=clamp01(motion.reveal*1.8-.2)
      if(elapsed>=450 && !assembleStarted){assembleStarted=true;scene.value?.playAssemble?.(1700,0)}
    }
    effects(dt)
  }
  function exit(sample,dt) {
    motion.exiting=true
    motion.exitUi=sample.exitUi;motion.tileReveal=sample.tileReveal
    if(sample.dissolve && !dissolveStarted){dissolveStarted=true;scene.value?.playDissolve?.(800)}
    effects(dt)
  }
  function restore(){motion.exiting=false;motion.exitUi=0;motion.tileReveal=1;dissolveStarted=false;scene.value?.resetDissolve?.()}
  return {motion,frame,exit,restore}
}
