// Port of rhine-lock transition.ts + App.svelte at a4df68c, AGPL-3.0-or-later.
// Geometry and cue equations are unchanged; the card holds a live Vue viewport.
export const clamp01 = t => Math.max(0, Math.min(1, t))
export const easeInOutCubic = t => t < .5 ? 4*t*t*t : 1-Math.pow(-2*t+2,3)/2
export function smooth(a,b,t) { const x=clamp01((t-a)/(b-a)); return x*x*(3-2*x) }
export const follow = (current,target,rate,dt) => current+(target-current)*(1-Math.exp(-dt*rate))
export function landscapeTile(width,height) {
  const k=Math.min(width/1920,height/1080)
  return { x:300*k,y:337*k,w:376*k,h:263*k }
}
export const isCompact = (width,height) => width<=height || width<1000 || height<620
export function transitionTarget(width,height,rect) {
  if(!isCompact(width,height))return landscapeTile(width,height)
  const w=Math.min(rect?.width||168,width-24),h=Math.min(rect?.height||w*.7,height-24)
  const x=Math.max(12,Math.min(rect?.left??(width-w)/2,width-w-12))
  const y=Math.max(12,Math.min(rect?.top??height*.17,height-h-12))
  return {x,y,w,h}
}
export function cardPose(e,target,{width:vw,height:vh}) {
  const scale=Math.exp(Math.log(Math.min(target.w/vw,target.h/vh))*e)
  const p0={x:vw/2,y:vh/2}, p2={x:target.x+target.w/2,y:target.y+target.h/2}
  const p1={x:p0.x*.55+p2.x*.45,y:Math.min(p0.y,p2.y)-vh*.16}
  const u=1-e, cx=u*u*p0.x+2*u*e*p1.x+e*e*p2.x, cy=u*u*p0.y+2*u*e*p1.y+e*e*p2.y
  const arc=Math.sin(Math.PI*e)
  return { x:cx-vw/2,y:cy-vh/2,cx,cy,scale,tilt:-13*arc,radius:18*arc/scale,shadow:.34*arc,
    transform:`translate(${cx-vw/2}px, ${cy-vh/2}px) perspective(1800px) rotateY(${-13*arc}deg) scale(${scale})`,
    boxShadow:arc>.01?`0 ${26/scale}px ${70/scale}px rgba(44,36,24,${.34*arc})`:'none' }
}
export function entryFrame(t) {
  return {draw:easeInOutCubic(clamp01(t/600)),shift:1-Math.pow(1-clamp01((t-650)/300),3),
    fade:1-Math.pow(clamp01((t-800)/500),2),zoom:Math.pow(clamp01((t-800)/500),3),
    reveal:1-Math.pow(1-clamp01((t-700)/800),3),ready:t>=1300}
}
export function exitFrame(t) {
  return {exitUi:smooth(180,600,t),dissolve:t>=220,e:1-easeInOutCubic(clamp01((t-560)/660)),
    cardOpacity:smooth(380,600,t),corners:smooth(700,950,t)*(1-smooth(1120,1220,t)),
    desat:1-smooth(600,1150,t),captionOpacity:smooth(600,760,t)*(1-smooth(1000,1150,t)),
    tileReveal:1-smooth(420,620,t),done:t>=1230}
}
