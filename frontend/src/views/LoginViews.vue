<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RhineMark from '../components/rhine/RhineMark.vue'
import RhineClock from '../components/rhine/RhineClock.vue'
import RhineScene from '../components/rhine/RhineScene.vue'
import { enterArchive } from '../components/rhine/loginTransition.js'
import { useRhineMotion } from '../components/rhine/useRhineMotion.js'
import { isCompact,transitionTarget } from '../components/rhine/motionMath.js'
import RhineBoot from '../components/rhine/RhineBoot.vue'
import RhineReticle from '../components/rhine/RhineReticle.vue'
import RhineCallouts from '../components/rhine/RhineCallouts.vue'
import { archiveTransition } from '../components/rhine/archiveTransition.js'

const route = useRoute()
const router = useRouter()
const loginName = ref('')
const password = ref('')
const submitting = ref(false)
const error = ref('')
const attempts=ref(0),errorReplay=ref(0)
const paused = ref(false)
const showPassword = ref(false)
const granted = ref(false)
const loginElement = ref(null)
const lifetime = new AbortController()
let transitionAbort
onUnmounted(() => {lifetime.abort();transitionAbort?.abort()})
const phase = computed(() => granted.value ? 'granted' : submitting.value ? 'verifying' : error.value ? 'denied' : 'ready')
const status = computed(() => granted.value ? '身份已确认 · 正在进入资料库' : submitting.value ? '验证中' : error.value ? '验证未通过' : '等待登录')
const scene=ref(null),pointer=reactive({x:.5,y:.5}),projectedAnchor=ref(null)
const {motion,frame,exit,restore}=useRhineMotion(phase,scene)
const viewport=reactive({width:1920,height:1080})
const anchor=computed(()=>projectedAnchor.value || {x:viewport.width*.325,y:viewport.height*.22+viewport.width*.65*175/600})
const compact=computed(()=>isCompact(viewport.width,viewport.height))
const motionStyle=computed(()=>({'--stage-k':Math.min(viewport.width/1920,viewport.height/1080),'--ui-reveal':motion.reveal,'--exit-ui':motion.exitUi,'--tile-reveal':motion.tileReveal,
  '--boot-k':compact.value?Math.min(1,viewport.width/480):Math.min(viewport.width/1920,viewport.height/1080),
  '--reticle-k':compact.value?Math.min(.65,Math.max(.45,viewport.width/900)):Math.min(viewport.width/1920,viewport.height/1080),
  '--header-opacity':Math.min(1,motion.reveal*2.2)*(1-motion.exitUi),'--panel-opacity':(1-Math.max(0,motion.exitUi-.85)/.15)*Math.min(1,motion.reveal*1.6),
  '--panel-out':Math.pow(motion.exitUi,3)*960+'px','--panel-yaw':(-6-(pointer.x-.5)*4.4)+'deg','--panel-pitch':((pointer.y-.5)*2.8)+'deg'}))
function resize(){const root=globalThis.document?.documentElement;viewport.width=root?.getBoundingClientRect?.().width||root?.clientWidth||innerWidth;viewport.height=innerHeight}
onMounted(()=>{resize();addEventListener('resize',resize)})
onUnmounted(()=>removeEventListener('resize',resize))
function point(event){pointer.x=event.clientX/viewport.width;pointer.y=event.clientY/viewport.height}
watch(()=>route.path,path=>{
  if(granted.value && archiveTransition.active && path!=='/library'){
    transitionAbort?.abort();granted.value=false;restore()
  }
})

async function submitLogin() {
  if (submitting.value || !motion.ready) return
  transitionAbort=new AbortController()
  submitting.value = true
  attempts.value++
  error.value = ''
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login_name: loginName.value, password: password.value }),
    })
    if(lifetime.signal.aborted)return
    if(!response.ok)errorReplay.value++
    if (response.status === 401) error.value = '用户名或密码错误'
    else if (response.status === 403) error.value = '来源不被允许'
    else if (!response.ok) error.value = '登录失败，请稍后再试'
    else {
      password.value = ''
      const focused=globalThis.document?.activeElement
      if(loginElement.value?.contains?.(focused))focused?.blur?.()
      if(compact.value)globalThis.scrollTo?.({top:0,left:0,behavior:'auto'})
      await enterArchive(async () => {
        await router.replace('/library')
        if (!lifetime.signal.aborted && route.path !== '/library') throw new Error('session-unavailable')
        granted.value = true
      }, () => transitionTarget(viewport.width,viewport.height,loginElement.value?.querySelector?.('.specimen-tile')?.getBoundingClientRect()), transitionAbort.signal, exit)
    }
  } catch (failure) {
    granted.value = false
    errorReplay.value++
    restore()
    error.value = failure?.message === 'session-unavailable' ? '登录状态未能确认，请重新登录。' : '登录失败，请稍后再试'
  }
  finally { submitting.value = false }
}
</script>

<template>
  <main ref="loginElement" class="login-page" :data-phase="phase" :data-layout="compact?'compact':'landscape'" :style="motionStyle" @pointermove="point">
    <a class="skip-link" href="#login-name">跳到登录表单</a>
    <RhineScene ref="scene" :phase="phase" :paused="paused" :motion="motion" :pointer="pointer" @frame="frame" @anchor="projectedAnchor=$event" />
    <RhineBoot :motion="motion" />
    <RhineReticle :phase="phase" :motion="motion" :anchor="anchor" :attempt="attempts" :replay="errorReplay" />
    <RhineCallouts v-if="!compact" :points="anchor" :motion="motion" :scale="Math.min(viewport.width/1920,viewport.height/1080)"/>
    <header class="login-header">
      <a class="login-wordmark" href="/login" aria-label="PersonalRAG 登录">
        <strong>PERSONAL RAG</strong><span>SYNTHESIZE INFORMATION</span><span class="wordmark-analysis">ARCHIVE <b>OS</b></span>
      </a>
      <RhineClock />
    </header>
    <div class="login-layout">
      <section class="login-intro" aria-label="PersonalRAG 个人资料库">
        <div class="specimen-label"><span class="signal-dot"></span> PERSONAL KNOWLEDGE ARCHIVE</div>
        <div class="specimen-tile"><RhineMark /><span>PERSONAL RAG</span><small>记录 · 整理 · 检索</small></div>
        <div class="specimen-caption"><span>个人资料库</span><p>让知识归档，让线索相连。</p></div>
      </section>
      <section class="login-panel" aria-labelledby="login-title" :inert="!motion.ready || undefined">
        <div class="profile-surface" aria-hidden="true"></div>
        <div class="profile-topline"><span>■ SECTION PROFILE</span><RhineMark /></div>
        <div class="profile-identity">
          <div class="profile-photo" aria-hidden="true">
            <svg viewBox="0 0 100 124"><defs><pattern id="profile-dots" width="3" height="3" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r=".6" fill="#ffffff" fill-opacity=".24" /></pattern></defs><path id="operator-silhouette" d="M50 14C63 14 71 24 71 38C71 50 66 60 59 65L60 72C85 79 101 92 101 124H-1C-1 92 15 79 40 72L41 65C34 60 29 50 29 38C29 24 37 14 50 14Z" fill="currentColor"/><use href="#operator-silhouette" fill="url(#profile-dots)" /></svg>
            <span>PERSONAL ACCESS</span>
          </div>
          <div class="profile-title"><span class="operator-label">OPERATOR</span><h1 id="login-title">身份认证</h1><p>登录你的个人资料库</p><span class="auth-status" :class="phase" aria-live="polite" aria-atomic="true"><i></i>{{ status }}</span></div>
        </div>
        <div class="profile-data"><span>资料类型 <b>TXT / MARKDOWN</b></span><span>访问方式 <b>个人账号</b></span></div>
        <p v-if="route.query.reason === 'session-unavailable'" role="status">暂时无法检查登录状态，请稍后再试。</p>
        <form class="login-form" :aria-busy="submitting" @submit.prevent="submitLogin">
          <div class="form-field"><label for="login-name"><span>用户名</span><small>ACCOUNT</small></label><input id="login-name" v-model="loginName" autocomplete="username" placeholder="输入用户名" required :disabled="submitting" /></div>
          <div class="form-field"><label for="password"><span>密码</span><small>AUTHORIZATION KEY</small></label><div class="password-field"><input id="password" v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="输入密码" required :disabled="submitting" :aria-describedby="error ? 'login-error' : undefined" /><button type="button" class="password-toggle" :aria-pressed="showPassword" :disabled="submitting" @click="showPassword = !showPassword">{{ showPassword ? '隐藏' : '显示' }}</button></div></div>
          <p v-if="error" id="login-error" role="alert">{{ error }}<small>请检查后重新登录。</small></p>
          <button class="primary login-submit" type="submit" :disabled="submitting"><span>{{ granted ? '验证通过 · 正在进入' : submitting ? '正在验证身份…' : '登录资料库' }}</span><span aria-hidden="true">{{ granted ? '✓' : submitting ? '···' : '↗' }}</span></button>
        </form>
        <p class="login-help">还没有账号？<a href="/register">注册账号</a></p>
      </section>
    </div>
    <footer class="login-footer"><span><RhineMark /> PERSONALRAG / 个人知识档案</span><button type="button" :aria-pressed="paused" :disabled="granted" @click="paused = !paused">{{ paused ? '继续动态场景' : '暂停动态场景' }}</button><a href="https://github.com/tmc5csxr9m-cpu/rhine-lock" target="_blank" rel="noopener noreferrer">界面源自 rhine-lock</a><a href="/assets/source/personalrag-frontend-source.zip" download>前端源码</a><a href="/assets/licenses/rhine-lock-AGPL-3.0.txt" target="_blank" rel="noopener noreferrer">AGPL-3.0</a></footer>
  </main>
</template>

