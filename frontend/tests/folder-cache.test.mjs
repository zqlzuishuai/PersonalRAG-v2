import test from 'node:test'
import assert from 'node:assert/strict'
import { createFolderCache } from '../src/data/folderCache.js'

test('concurrent directory readers share one request, including empty results until expiry', async () => {
  let calls=0,now=0,finish
  const cache=createFolderCache(()=>{calls++;return new Promise(resolve=>{finish=resolve})},{ttlMs:30,now:()=>now})
  const first=cache.load(null),second=cache.load(null)
  await Promise.resolve()
  assert.equal(calls,1)
  finish([])
  assert.deepEqual(await first,[])
  assert.deepEqual(await second,[])
  await cache.load(null)
  assert.equal(calls,1)
  now=31
  const expired=cache.load(null)
  await Promise.resolve()
  assert.equal(calls,2)
  finish([{id:'new-folder'}])
  assert.deepEqual(await expired,[{id:'new-folder'}])
})

test('invalidation after a folder write prevents an older response from overwriting fresh data', async () => {
  const pending=[]
  const cache=createFolderCache(()=>new Promise(resolve=>pending.push(resolve)))
  const old=cache.load('parent')
  await Promise.resolve()
  cache.clear()
  const fresh=cache.load('parent')
  await Promise.resolve()
  pending[1]([{id:'after-write'}])
  await fresh
  pending[0]([{id:'before-write'}])
  await old
  assert.deepEqual(await cache.load('parent'),[{id:'after-write'}])
  assert.equal(pending.length,2)
})

test('failed requests can be retried and different parents and view instances stay isolated', async () => {
  let calls=0
  const fetcher=async parent=>{if(++calls===1)throw new Error('offline');return [parent]}
  const first=createFolderCache(fetcher),second=createFolderCache(fetcher)
  await assert.rejects(first.load(null),/offline/)
  assert.deepEqual(await first.load(null),[null])
  assert.deepEqual(await first.load('child'),['child'])
  await second.load(null)
  assert.equal(calls,4)
})
