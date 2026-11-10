<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const libraryLink = computed(() => ({ path: '/library', query: { folder: route.query.folder } }))
const entries = ref([])
const tab = ref('documents')
const offset = ref(0)
const hasNext = ref(false)
const loading = ref(false)
const restoring = ref(null)
const loadError = ref('')
const restoreError = ref('')
const notice = ref('')
const PAGE_SIZE = 20

async function request(url, options) {
  const response = await fetch(url, options)
  if (response.status === 401) await router.replace('/login')
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.error || '服务暂时不可用，请稍后重试。')
  }
  if (response.status !== 204) return response.json()
}

async function load(start = offset.value) {
  loading.value = true
  loadError.value = ''
  try {
    const params = new URLSearchParams({ limit: PAGE_SIZE + 1, offset: start })
    const result = await request('/api/trash/' + tab.value + '?' + params)
    const items = result[tab.value]
    entries.value = items.slice(0, PAGE_SIZE)
    hasNext.value = items.length > PAGE_SIZE
    offset.value = start
  } catch (error) {
    loadError.value = error.message
  } finally {
    loading.value = false
  }
}

function selectTab(next) {
  if (next === tab.value || loading.value || restoring.value) return
  tab.value = next
  entries.value = []
  offset.value = 0
  hasNext.value = false
  notice.value = ''
  restoreError.value = ''
  load(0)
}

async function restore(item) {
  if (restoring.value) return
  const isFolder = tab.value === 'folders'
  restoring.value = item.id
  restoreError.value = ''
  notice.value = ''
  try {
    const resource = isFolder ? 'folders' : 'documents'
    await request('/api/' + resource + '/' + encodeURIComponent(item.id) + '/restore', { method: 'POST' })
    notice.value = isFolder
      ? '已恢复「' + item.name + '」及同批回收的内容。'
      : '已恢复「' + item.title + '」。'
    await load(entries.value.length === 1 && offset.value > 0 ? offset.value - PAGE_SIZE : offset.value)
  } catch (error) {
    restoreError.value = error.message
  } finally {
    restoring.value = null
  }
}

onMounted(() => load())
</script>

<template>
  <main class="trash">
    <RouterLink :to="libraryLink">← 返回资料库</RouterLink>
    <h1>回收站</h1><p class="page-description">查看已回收的资料与文件夹，恢复到原目录。</p>
    <nav aria-label="回收站内容">
      <button type="button" :aria-pressed="tab === 'documents'" :disabled="loading || Boolean(restoring)"
        @click="selectTab('documents')">单份资料</button>
      <button type="button" :aria-pressed="tab === 'folders'" :disabled="loading || Boolean(restoring)"
        @click="selectTab('folders')">文件夹</button>
    </nav>
    <p v-if="tab === 'documents'">恢复后的资料会回到原目录。</p>
    <p v-else>每项代表一次整树回收，包含当时随目录一起回收的内容。</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="restoreError" class="error" role="alert">{{ restoreError }}</p>

    <div class="state-region documents-state" :aria-busy="loading">
      <Transition name="state">
        <div v-if="loading" key="loading" role="status"><span class="sr-only">正在读取回收站…</span><ul class="trash-list skeleton-list" aria-hidden="true"><li v-for="row in 3" :key="row"><div class="skeleton-copy"><span class="skeleton-line"></span><span class="skeleton-line skeleton-short"></span></div><span class="skeleton-line skeleton-action"></span></li></ul></div>
        <div v-else-if="loadError" key="error" class="empty"><p class="error" role="alert">{{loadError}}</p><button type="button" @click="load()">重试</button></div>
        <p v-else-if="!entries.length" key="empty" class="empty">{{tab === 'folders' ? '回收站里没有文件夹。' : '回收站里没有单独回收的资料。'}}</p>
        <div v-else key="content">
          <TransitionGroup name="list-item" tag="ul" class="trash-list" appear>
            <li v-for="item in entries" :key="item.id"><div><strong>{{tab === 'folders' ? item.name : item.title}}</strong><small>移入时间：{{new Date(item.deleted_at).toLocaleString('zh-CN')}}</small></div><button type="button" :disabled="Boolean(restoring)" @click="restore(item)">{{restoring === item.id ? '正在恢复…' : '恢复'}}</button></li>
          </TransitionGroup>
          <nav v-if="offset || hasNext" class="pagination" aria-label="回收站分页"><button type="button" :disabled="!offset || Boolean(restoring)" @click="load(offset - PAGE_SIZE)">上一页</button><span>第 {{offset / PAGE_SIZE + 1}} 页</span><button type="button" :disabled="!hasNext || Boolean(restoring)" @click="load(offset + PAGE_SIZE)">下一页</button></nav>
        </div>
      </Transition>
    </div>
  </main>
</template>

