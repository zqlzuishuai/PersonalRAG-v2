// Adapted from rhine-lock DecodeText.svelte, AGPL-3.0-or-later.
const GLYPHS='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#%&*+=/<>'
export function decodeFrame(text,elapsed,duration=32*text.length+180){
  const p=Math.min(1,Math.max(0,elapsed/duration))
  if(p>=1)return {solid:text,tail:'',done:true}
  const n=Math.floor(p*(text.length+3)),solid=Math.max(0,Math.min(text.length,n-3))
  let tail=''
  for(let i=solid;i<Math.min(text.length,n);i++)tail+=text[i]===' '?' ':GLYPHS[(i*7+Math.floor(elapsed/45)*13+text.charCodeAt(i))%GLYPHS.length]
  return {solid:text.slice(0,solid),tail,done:false}
}
