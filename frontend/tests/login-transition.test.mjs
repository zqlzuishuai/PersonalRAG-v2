import {test} from 'node:test'
import assert from 'node:assert/strict'
import {enterArchive} from '../src/components/rhine/loginTransition.js'
import {archiveTransition} from '../src/components/rhine/archiveTransition.js'

function clock(){
  let id=0, callbacks=new Map()
  globalThis.innerWidth=1920;globalThis.innerHeight=1080
  globalThis.matchMedia=()=>({matches:false})
  globalThis.requestAnimationFrame=cb=>{callbacks.set(++id,cb);return id}
  globalThis.cancelAnimationFrame=id=>callbacks.delete(id)
  return now=>{const batch=[...callbacks.values()];callbacks.clear();for(const cb of batch)cb(now)}
}
test('the guarded destination mounts once, but login stays until its fullscreen handoff',async()=>{
  const tick=clock();let navigations=0,last
  const done=enterArchive(async()=>{navigations++},null,new AbortController().signal,s=>{last=s})
  await Promise.resolve();tick(1000);tick(1560)
  assert.equal(navigations,1)
  assert.equal(archiveTransition.active,true)
  assert.equal(last.e,1)
  tick(2229);assert.equal(archiveTransition.active,true)
  tick(2230);await done
  assert.equal(last.e,0);assert.equal(archiveTransition.active,false)
})
test('cancellation clears the presentation without a second route or delayed callback',async()=>{
  const tick=clock(),controller=new AbortController();let calls=0
  const done=enterArchive(async()=>{calls++},null,controller.signal)
  await Promise.resolve();tick(0);tick(500);controller.abort();await done;tick(2000)
  assert.equal(calls,1);assert.equal(archiveTransition.active,false)
})
test('guard rejection cannot leave an invisible active overlay',async()=>{
  clock()
  await assert.rejects(enterArchive(async()=>{throw Error('guard')},null,new AbortController().signal),/guard/)
  assert.equal(archiveTransition.active,false)
})
test('reduced motion hands over immediately without requesting animation frames',async()=>{
  clock();globalThis.matchMedia=()=>({matches:true});let calls=0
  globalThis.requestAnimationFrame=()=>{throw Error('unexpected animation')}
  await enterArchive(async()=>{calls++},null,new AbortController().signal)
  assert.equal(calls,1);assert.equal(archiveTransition.active,false)
})

test('enabling reduced motion during flight stops the large transform immediately',async()=>{
  const tick=clock(),preference={matches:false}
  globalThis.matchMedia=()=>preference
  const done=enterArchive(async()=>{},null,new AbortController().signal)
  await Promise.resolve();tick(0);tick(400)
  assert.equal(archiveTransition.active,true)
  preference.matches=true;tick(450);await done
  assert.equal(archiveTransition.active,false)
})

test('rotating during flight hands over cleanly rather than stretching the old viewport',async()=>{
  const tick=clock()
  const done=enterArchive(async()=>{},null,new AbortController().signal)
  await Promise.resolve();tick(0);tick(400)
  assert.equal(archiveTransition.active,true)
  globalThis.innerWidth=375;globalThis.innerHeight=812
  tick(450);await Promise.resolve()
  assert.equal(archiveTransition.active,false)
  await done
})
