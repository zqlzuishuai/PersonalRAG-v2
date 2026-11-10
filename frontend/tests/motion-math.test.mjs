import { test } from 'node:test'
import assert from 'node:assert/strict'
import { cardPose, entryFrame, exitFrame } from '../src/components/rhine/motionMath.js'

test('the archived viewport keeps one scale, follows an upward arc, and lands exactly fullscreen', () => {
  const viewport = { width: 1920, height: 1080 }
  const target = { x: 300, y: 337, w: 376, h: 263 }
  const full = cardPose(0, target, viewport)
  assert.equal(full.scale, 1)
  assert.equal(full.x, 0); assert.equal(full.y, 0); assert.ok(Math.abs(full.tilt) < 1e-10)
  const tile = cardPose(1, target, viewport)
  assert.ok(Math.abs(tile.scale - 376 / 1920) < 1e-10)
  assert.ok(Math.abs(tile.cx - 488) < 1e-10)
  assert.ok(Math.abs(tile.cy - 468.5) < 1e-10)
  const mid = cardPose(.5, target, viewport)
  assert.ok(mid.cy < (540 + 468.5) / 2)
  assert.equal(mid.tilt, -13)
  assert.ok(Math.abs(mid.scale ** 2 - tile.scale) < 1e-10)
  assert.ok(mid.radius > 0 && mid.shadow > 0)
})

test('the real scene remains through dissolution; the endpoint is the original 1230ms handoff', () => {
  assert.equal(exitFrame(0).cardOpacity, 0)
  assert.equal(exitFrame(219).dissolve, false)
  assert.equal(exitFrame(220).dissolve, true)
  assert.equal(exitFrame(560).e, 1)
  assert.equal(exitFrame(1220).e, 0)
  assert.equal(exitFrame(1229).done, false)
  assert.equal(exitFrame(1230).done, true)
})

test('the original plain boot draws the mark before revealing UI and enabling the form', () => {
  assert.equal(entryFrame(0).draw, 0)
  assert.equal(entryFrame(600).draw, 1)
  assert.equal(entryFrame(699).reveal, 0)
  assert.equal(entryFrame(1299).ready, false)
  assert.equal(entryFrame(1300).ready, true)
  assert.equal(entryFrame(1500).reveal, 1)
})
