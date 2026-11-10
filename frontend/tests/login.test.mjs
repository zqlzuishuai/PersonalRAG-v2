import assert from 'node:assert/strict'
import { readFile, writeFile, unlink } from 'node:fs/promises'
import { test } from 'node:test'
import { parse, compileScript } from '@vue/compiler-sfc'
import { createRenderer, nextTick, reactive } from 'vue'

// Mount the real SFC without a browser or a server; only the HTTP boundary is mocked.
const source = await readFile(new URL('../src/views/LoginViews.vue', import.meta.url), 'utf8')
const { descriptor } = parse(source)
const compiled = compileScript(descriptor, { id: 'login-regression', inlineTemplate: true }).content
  .replace(/import\s+\{([^}]+)\}\s+from\s+['"]vue-router['"];?/g,
    'const { useRoute, useRouter } = globalThis.__loginTestRouter;')
  .replace(/import\s+(\w+)\s+from\s+['"][^'"]+\.vue['"];?/g, 'const $1 = { render: () => null };')
  .replaceAll('../components/rhine/', './src/components/rhine/')
const moduleUrl = new URL(`../.login-test-${process.pid}.mjs`, import.meta.url)
let Login
globalThis.__loginTestRouter = {
  useRoute: () => globalThis.__loginTestRoute,
  useRouter: () => ({ replace: async path => {
    const target = globalThis.__loginGuardRedirect || path
    globalThis.__loginDestination = target
    globalThis.__loginTestRoute.path = target.split('?')[0]
  } }),
}
try {
  await writeFile(moduleUrl, compiled)
  Login = (await import(moduleUrl.href)).default
} finally {
  await unlink(moduleUrl).catch(() => {})
}

globalThis.Document = class Document {}
globalThis.document = Object.assign(new Document(), { activeElement: null })
globalThis.matchMedia = () => ({ matches: true })
globalThis.innerWidth=1920;globalThis.innerHeight=1080
globalThis.addEventListener=()=>{};globalThis.removeEventListener=()=>{}
function node(type, text = '') { return { type, tagName: type.toUpperCase(), text, props: {}, children: [], parent: null, addEventListener() {}, getRootNode() { return globalThis.document } } }
const renderer = createRenderer({
  insertStaticContent(content, parent, anchor) {
    const n = node('#static', content)
    n.parent = parent
    const index = anchor ? parent.children.indexOf(anchor) : -1
    parent.children.splice(index < 0 ? parent.children.length : index, 0, n)
    return [n, n]
  },
  createElement: type => node(type), createText: text => node('#text', text), createComment: text => node('#comment', text),
  setText: (n, text) => { n.text = text }, setElementText: (n, text) => { n.text = text; n.children = [] },
  parentNode: n => n.parent, nextSibling: n => n.parent?.children[n.parent.children.indexOf(n) + 1] ?? null,
  patchProp: (n, key, old, value) => { n.props[key] = value },
  insert(n, parent, anchor = null) {
    if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1)
    n.parent = parent
    const index = anchor ? parent.children.indexOf(anchor) : -1
    parent.children.splice(index < 0 ? parent.children.length : index, 0, n)
  },
  remove(n) { if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1) },
})
function find(root, predicate) {
  if (predicate(root)) return root
  for (const child of root.children) { const found = find(child, predicate); if (found) return found }
}
function text(root) { return root.text + root.children.map(text).join('') }
async function mount() {
  globalThis.__loginDestination = null
  globalThis.__loginGuardRedirect = null
  globalThis.__loginTestRoute = reactive({ path: '/login', query: {} })
  const root = node('root')
  const app = renderer.createApp(Login)
  app.mount(root)
  const field = id => find(root, n => n.props.id === id)
  field('login-name').props['onUpdate:modelValue']('test-operator')
  field('password').props['onUpdate:modelValue'](' test password ')
  await nextTick()
  return { root, app, field, submit: () => find(root, n => n.type === 'form').props.onSubmit({ preventDefault() {} }) }
}

test('authentication states follow HTTP results, prevent duplicate requests, and permit retry', async () => {
  const previousFetch = globalThis.fetch
  let resolveRequest, requests = []
  globalThis.fetch = (url, options) => {
    requests.push({ url, options })
    return new Promise(resolve => { resolveRequest = resolve })
  }
  const view = await mount()
  try {
    const phase = () => find(view.root, n => n.props['data-phase'])?.props['data-phase']
    assert.equal(phase(), 'ready')
    const pending = view.submit()
    await nextTick()
    assert.equal(phase(), 'verifying')
    assert.equal(view.field('password').props.disabled, true)
    await view.submit()
    assert.equal(requests.length, 1)
    assert.equal(requests[0].url, '/api/auth/login')
    assert.deepEqual(JSON.parse(requests[0].options.body), { login_name: 'test-operator', password: ' test password ' })
    resolveRequest({ status: 401, ok: false })
    await pending; await nextTick()
    assert.equal(phase(), 'denied')
    assert.match(text(view.root), /用户名或密码错误/)
    assert.equal(globalThis.__loginDestination, null)
    const retry = view.submit()
    resolveRequest({ status: 200, ok: true })
    await retry; await nextTick()
    assert.equal(phase(), 'granted')
    assert.equal(globalThis.__loginDestination, '/library')
    assert.equal(view.field('password').value, '')
  } finally { view.app.unmount(); globalThis.fetch = previousFetch }
})

test('network and origin failures leave a usable form without granting access', async () => {
  const previousFetch = globalThis.fetch
  const view = await mount()
  try {
    globalThis.fetch = async () => { throw new Error('offline') }
    await view.submit(); await nextTick()
    assert.match(text(view.root), /登录失败/)
    assert.equal(view.field('password').props.disabled, false)
    globalThis.fetch = async () => ({ status: 403, ok: false })
    await view.submit(); await nextTick()
    assert.match(text(view.root), /来源不被允许/)
    assert.equal(globalThis.__loginDestination, null)
  } finally { view.app.unmount(); globalThis.fetch = previousFetch }
})

test('a session guard redirect after a successful POST restores the form for retry', async () => {
  const previousFetch = globalThis.fetch
  globalThis.fetch = async () => ({ status: 200, ok: true })
  try {
    for (const target of ['/login', '/login?reason=session-unavailable']) {
      const view = await mount()
      try {
        globalThis.__loginGuardRedirect = target
        await view.submit(); await nextTick()
        assert.equal(find(view.root,n=>n.props['data-phase'])?.props['data-phase'], 'denied')
        assert.equal(view.field('password').props.disabled, false)
        assert.match(text(view.root), /登录状态未能确认/)
        globalThis.__loginGuardRedirect = null
        await view.submit(); await nextTick()
        assert.equal(globalThis.__loginDestination, '/library')
      } finally { view.app.unmount() }
    }
  } finally { globalThis.fetch = previousFetch }
})

test('browser back during the retained exit cancels and restores login', async () => {
  const previousFetch=globalThis.fetch
  globalThis.fetch=async()=>({status:200,ok:true})
  const view=await mount()
  const previousMedia=globalThis.matchMedia
  globalThis.matchMedia=()=>({matches:false})
  let id=0,callbacks=new Map()
  globalThis.requestAnimationFrame=cb=>{callbacks.set(++id,cb);return id}
  globalThis.cancelAnimationFrame=id=>callbacks.delete(id)
  try{
    const done=view.submit()
    for(let i=0;i<8;i++)await Promise.resolve()
    globalThis.__loginTestRoute.path='/login'
    await nextTick();await done;await nextTick()
    assert.equal(find(view.root,n=>n.props['data-phase'])?.props['data-phase'],'ready')
    assert.equal(callbacks.size,0)
    assert.equal(view.field('password').props.disabled,false)
  }finally{view.app.unmount();globalThis.fetch=previousFetch;globalThis.matchMedia=previousMedia}
})

test('a late login response after leaving the page cannot navigate',async()=>{
  const previousFetch=globalThis.fetch
  let finish
  globalThis.fetch=()=>new Promise(resolve=>{finish=resolve})
  const view=await mount()
  try{
    const done=view.submit();view.app.unmount()
    finish({status:200,ok:true});await done
    assert.equal(globalThis.__loginDestination,null)
  }finally{globalThis.fetch=previousFetch}
})

