<script setup>
import { computed, ref, provide, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RhineMark from './components/rhine/RhineMark.vue'
import RhineClock from './components/rhine/RhineClock.vue'
import AppIcon from './components/AppIcon.vue'
import LoginView from './views/LoginViews.vue'
import RegisterView from './views/RegisterView.vue'
import { archiveTransition } from './components/rhine/archiveTransition.js'
const sourceBuild = new URL(import.meta.url).pathname.split('/').at(-1).replace(/\.js$/, '')
const sourceDownloadUrl = import.meta.env.DEV ? '/assets/source/personalrag-frontend-source.zip' : '/assets/source/personalrag-frontend-source-'+sourceBuild+'.zip'
const route = useRoute()
const router = useRouter()
const isLogin = computed(() => route.path === '/login')
const isRegistration = computed(() => route.path === '/register')
const navigation = [
  { path: '/library', label: '我的资料', code: 'ARCHIVE', icon: 'folder' },
  { path: '/search', label: '正文检索', code: 'RETRIEVAL', icon: 'search' },
  { path: '/trash', label: '回收站', code: 'RECOVERY', icon: 'trash' },
]
const current = computed(() => navigation.find(item => route.path.startsWith(item.path)) || navigation[0])
const loggingOut = ref(false)
const logoutError = ref('')
const railCollapsed = ref(false)
const compactLayout = ref(false)
let layoutQuery
const updateLayout = () => { compactLayout.value = layoutQuery.matches }
onMounted(() => { layoutQuery = window.matchMedia('(max-width:760px)'); updateLayout(); layoutQuery.addEventListener('change', updateLayout) })
onUnmounted(() => { layoutQuery?.removeEventListener('change', updateLayout) })
provide('workspaceFoldersInline', computed(() => railCollapsed.value || compactLayout.value))
async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  logoutError.value = ''
  try {
    const response = await fetch('/api/auth/logout', { method: 'POST' })
    if (!response.ok && response.status !== 401) throw new Error()
    await router.replace('/login')
  } catch {
    logoutError.value = '退出失败，请重试。'
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <LoginView v-if="isLogin || archiveTransition.active" />
  <RegisterView v-if="isRegistration" />
  <div v-if="!isLogin && !isRegistration" class="archive-viewport" :class="{ 'is-flying': archiveTransition.active }"
    :style="archiveTransition.active ? archiveTransition.frameStyle : undefined" :inert="archiveTransition.active || undefined" :aria-hidden="archiveTransition.active || undefined">
  <div class="workspace" :class="{ 'is-rail-collapsed': railCollapsed }">
    <a class="skip-link" href="#workspace-content">跳到主要内容</a>
    <aside id="workspace-navigation" class="workspace-rail">
      <RouterLink to="/library" class="brand" aria-label="PersonalRAG 资料库首页">
        <span class="brand-mark"><RhineMark /></span><span>PersonalRAG<small>个人知识工作区</small></span>
      </RouterLink>
      <div class="nav-caption">资料空间</div><nav class="main-nav" aria-label="主导航">
        <RouterLink v-for="item in navigation" :key="item.path" :to="item.path"
          :class="{ active: current.path === item.path }" :aria-label="item.label" :title="item.label" :aria-current="current.path === item.path ? 'page' : undefined">
          <AppIcon :name="item.icon" /><span>{{ item.label }}<small>{{ item.code }}</small></span><i aria-hidden="true"></i>
        </RouterLink>
      </nav>
      <div id="workspace-folders"></div>
      <div class="rail-session"><span class="user-avatar"><AppIcon name="user" :size="18"/></span><span>个人工作区<small>个人账号</small></span></div>
      <button class="logout quiet-button" type="button" aria-label="退出登录" title="退出登录" :disabled="loggingOut" @click="logout">
        <AppIcon name="logout" :size="16"/><span>{{ loggingOut ? '正在退出…' : '退出登录' }}</span>
      </button>
    </aside>
    <div class="workspace-main">
    <header class="site-header"><button type="button" class="icon-button rail-toggle" :aria-label="railCollapsed?'展开侧栏':'折叠侧栏'" :aria-expanded="!railCollapsed" aria-controls="workspace-navigation" @click="railCollapsed=!railCollapsed"><AppIcon name="panel" :size="18"/></button><div id="workspace-breadcrumbs"></div><div class="workspace-heading"><AppIcon :name="current.icon" :size="17"/><RouterLink to="/library">工作区</RouterLink><span>/</span><p>{{ route.name === 'document' ? '资料详情' : current.label }}</p></div><div id="workspace-actions"></div><div class="workspace-clock"><RhineClock /></div></header>
    <p v-if="logoutError" class="session-error" role="alert">{{ logoutError }}</p>
    <div id="workspace-content" tabindex="-1">
      <RouterView v-slot="{ Component, route }">
        <Transition name="page" mode="out-in" :css="!archiveTransition.active">
          <component :is="Component" :key="route.path" />
        </Transition>
      </RouterView>
    </div>
    <footer class="site-footer"><span>PersonalRAG · 个人知识资料库</span><a href="https://github.com/tmc5csxr9m-cpu/rhine-lock" target="_blank" rel="noopener noreferrer">Rhine 登录视觉</a><a :href="sourceDownloadUrl" download>前端源码</a><a href="/assets/licenses/rhine-lock-AGPL-3.0.txt" target="_blank" rel="noopener noreferrer">AGPL-3.0</a></footer>
    </div>
  </div>
  <template v-if="archiveTransition.active">
    <div class="snapshot-shade" :style="{opacity:archiveTransition.shade}"></div>
    <i v-for="corner in ['tl','tr','bl','br']" :key="corner" class="snapshot-corner" :class="corner" :style="{opacity:archiveTransition.corners,transform:`scale(${archiveTransition.cornerScale})`}"></i>
  </template>
  </div>
  <div v-if="archiveTransition.active" class="snapshot-caption" :style="archiveTransition.captionStyle" aria-hidden="true">PERMISSION AUTHORIZED · PERSONAL ARCHIVE RESTORED</div>
</template>
