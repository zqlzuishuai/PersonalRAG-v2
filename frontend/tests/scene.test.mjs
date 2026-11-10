import assert from 'node:assert/strict'
import { readFile, writeFile, unlink } from 'node:fs/promises'
import { test } from 'node:test'
import { transformWithOxc } from 'vite'
import * as THREE from 'three'

// Run the real disposal method against Three objects without creating a GPU context.
// This verifies explicit disposal events, not actual driver memory reclamation.
const root = new URL('../', import.meta.url)
const stageUrl = new URL(`.rhine-stage-test-${process.pid}.mjs`, root)
const shaderUrl = new URL(`.rhine-shaders-test-${process.pid}.mjs`, root)
const stageSource = await readFile(new URL('src/components/rhine/scene/Stage.ts', root), 'utf8')
const shaderSource = await readFile(new URL('src/components/rhine/scene/shaders.ts', root), 'utf8')
const stageResult = await transformWithOxc(stageSource, 'Stage.ts')
const shaderResult = await transformWithOxc(shaderSource, 'shaders.ts')
let Stage
const oldLocation = globalThis.location
globalThis.location = { search: '' }
try {
  await writeFile(shaderUrl, shaderResult.code)
  await writeFile(stageUrl, stageResult.code.replace('"./shaders"', JSON.stringify(`./.rhine-shaders-test-${process.pid}.mjs`)))
  Stage = (await import(stageUrl.href)).Stage
} finally {
  globalThis.location = oldLocation
  await Promise.all([unlink(stageUrl), unlink(shaderUrl)])
}

test('scene cleanup disposes light shadow targets and mesh resources exactly once', () => {
  const stage = Object.create(Stage.prototype)
  const scene = new THREE.Scene()
  const light = new THREE.DirectionalLight()
  const shadow = new THREE.WebGLRenderTarget(16, 16)
  const geometry = new THREE.BoxGeometry()
  const material = new THREE.MeshBasicMaterial()
  light.shadow.map = shadow
  scene.add(light, new THREE.Mesh(geometry, material))
  const counts = { shadow: 0, geometry: 0, material: 0, renderer: 0, composer: 0 }
  for (const [name, object] of [['shadow', shadow], ['geometry', geometry], ['material', material]]) {
    object.addEventListener('dispose', () => { counts[name]++ })
  }
  Object.assign(stage, { disposed: false, raf: 1, scene, textures: [], environmentTarget: null,
    renderer: { dispose() { counts.renderer++ } }, composer: { dispose() { counts.composer++ } } })
  const oldWindow = globalThis.window, oldCancel = globalThis.cancelAnimationFrame
  globalThis.window = { removeEventListener() {} }
  globalThis.cancelAnimationFrame = () => {}
  try {
    stage.dispose()
    stage.dispose()
    assert.deepEqual(counts, { shadow: 1, geometry: 1, material: 1, renderer: 1, composer: 1 })
  } finally { globalThis.window = oldWindow; globalThis.cancelAnimationFrame = oldCancel }
})

test('a guard-rejected entry can restore the dissolved scene', () => {
  const stage = Object.create(Stage.prototype)
  Object.assign(stage, { dissolve: 1, dissolveAnim: { t0: 1, dur: .8 } })
  stage.resetDissolve()
  assert.equal(stage.dissolve, 0)
  assert.equal(stage.dissolveAnim, null)
})
