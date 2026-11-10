import {test} from 'node:test'
import assert from 'node:assert/strict'
import {isCompact,transitionTarget,landscapeTile,cardPose} from '../src/components/rhine/motionMath.js'

test('desktop keeps the accepted design coordinates, portrait and short screens use compact layout',()=>{
  assert.equal(isCompact(1440,810),false)
  assert.equal(isCompact(1024,768),false)
  assert.equal(isCompact(768,1024),true)
  assert.equal(isCompact(844,390),true)
  assert.deepEqual(transitionTarget(1440,810,{left:10,top:10,width:100,height:100}),landscapeTile(1440,810))
})
test('the mobile card starts at its visible DOM tile and remains in bounds after scrolling',()=>{
  assert.deepEqual(transitionTarget(375,812,{left:24,top:140,width:150,height:105}),{x:24,y:140,w:150,h:105})
  for(const [width,height] of [[320,568],[375,667],[430,932],[768,1024],[844,390]]){
    const target=transitionTarget(width,height,{left:-40,top:-300,width:180,height:126})
    assert.ok(target.x>=12 && target.y>=12)
    assert.ok(target.x+target.w<=width-12)
    assert.ok(target.y+target.h<=height-12)
    assert.equal(cardPose(0,target,{width,height}).scale,1)
  }
})
