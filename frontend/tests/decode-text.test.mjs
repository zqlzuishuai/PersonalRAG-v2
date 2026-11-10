import {test} from 'node:test'
import assert from 'node:assert/strict'
import {decodeFrame} from '../src/components/rhine/decodeText.js'
test('decoded text retains a stable prefix and at most three temporary glyphs',()=>{
  const text='VERIFYING IDENTITY'
  const start=decodeFrame(text,0,1000)
  assert.equal(start.solid,'');assert.equal(start.tail,'')
  const middle=decodeFrame(text,500,1000)
  assert.ok(text.startsWith(middle.solid));assert.ok(middle.tail.length<=3)
  assert.deepEqual(decodeFrame(text,1000,1000),{solid:text,tail:'',done:true})
})
