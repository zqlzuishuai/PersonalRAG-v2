import { archiveTransition, resetArchiveTransition } from './archiveTransition.js'
import { cardPose, exitFrame, transitionTarget } from './motionMath.js'

// Keep the login and its GPU scene mounted until the live destination reaches
// the exact final frame. There is no early snapshot swap or nonuniform scaling.
export async function enterArchive(navigate, origin, signal, onFrame=()=>{}) {
  if(signal.aborted) return
  archiveTransition.active=true
  try {
    await navigate()
    const preference=globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')
    if(signal.aborted || preference?.matches) return
    await new Promise((resolve,reject)=>{
      let raf=0, start=null, previous=null,initialViewport
      const abort=()=>{cancelAnimationFrame(raf);signal.removeEventListener('abort',abort);resolve()}
      signal.addEventListener('abort',abort,{once:true})
      const frame=now=>{
        if(signal.aborted){abort();return}
        if(preference?.matches){signal.removeEventListener('abort',abort);resolve();return}
        start??=now; previous??=now
        const t=now-start, sample=exitFrame(t), dt=Math.min(.05,(now-previous)/1000)
        previous=now
        try {
          const root=globalThis.document?.documentElement
          const viewport={width:root?.getBoundingClientRect?.().width||root?.clientWidth||innerWidth,height:innerHeight}
          initialViewport??=viewport
          if(Math.abs(viewport.width-initialViewport.width)>2 || Math.abs(viewport.height-initialViewport.height)>2){
            onFrame(exitFrame(1230),0);signal.removeEventListener('abort',abort);resolve();return
          }
          const target=typeof origin==='function'?origin():origin || transitionTarget(viewport.width,viewport.height)
          const pose=cardPose(sample.e,target,viewport)
          archiveTransition.frameStyle={transform:pose.transform,borderRadius:`${pose.radius}px`,boxShadow:pose.boxShadow,opacity:sample.cardOpacity,
            filter:`saturate(${1-.55*sample.desat}) brightness(${1+.04*sample.desat})`,width:viewport.width+'px',height:viewport.height+'px'}
          archiveTransition.corners=sample.corners
          archiveTransition.cornerScale=1/pose.scale
          archiveTransition.shade=.12*sample.desat
          const captionX=pose.cx-viewport.width*pose.scale/2
          archiveTransition.captionStyle={opacity:sample.captionOpacity,transform:`translate(${captionX}px, ${pose.cy+innerHeight*pose.scale/2+14}px)`,maxWidth:`${Math.max(0,viewport.width-captionX-16)}px`}
          onFrame(sample,dt)
          if(sample.done){signal.removeEventListener('abort',abort);resolve()}
          else raf=requestAnimationFrame(frame)
        } catch(error){signal.removeEventListener('abort',abort);reject(error)}
      }
      raf=requestAnimationFrame(frame)
    })
  } finally { resetArchiveTransition() }
}
