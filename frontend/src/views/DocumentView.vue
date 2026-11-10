<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import WorkOverlay from '../components/WorkOverlay.vue'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute()
const router = useRouter()
const endpoint = computed(() => '/api/documents/' + encodeURIComponent(route.params.documentId))
const libraryLink = computed(() => ({ path: '/library', query: { folder: route.query.folder } }))
const document = ref(null)
const confirmingRecycle = ref(false)
const recycling = ref(false)
const recycleError = ref('')
const versions = ref([])
const runsByVersion = ref({})
const runErrors = ref({})
const processingVersion = ref(null)
const processError = ref('')
const processingLabels = {
  queued: '等待处理',
  running: '处理中',
  succeeded: '处理完成',
  failed: '处理失败',
  cancelled: '已取消',
}
let processingPage = 0
let pollTimer
let disposed = false
const detailError = ref('')
const historyError = ref('')
const uploadError = ref('')
const notice = ref('')
const loading = ref(false)
const loadingHistory = ref(false)
const uploading = ref(false)
const uploadOpen=ref(false),uploadDirty=ref(false)
const editDirty=computed(()=>edit.value==='title'?editTitle.value!==document.value?.title:edit.value==='tags'?JSON.stringify(editTags.value)!==JSON.stringify(document.value?.tags??[]):edit.value==='folder'?(folderTrail.value.at(-1)?.id??null)!==(document.value?.folder_id??null):false)
const offset = ref(0)
const hasNext = ref(false)
const PAGE_SIZE = 20
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024
let detailRequest = 0
let historyRequest = 0


const edit = ref('')
const editTitle = ref('')
const editTags = ref([])
const folderTrail = ref([])
const folderOptions = ref([])
const loadingFolders = ref(false)
const editError = ref('')
const editNotice = ref('')
const saving = ref(false)
let folderRequest = 0

function startEdit(kind) {
  edit.value = kind
  editError.value = ''
  editNotice.value = ''
  if (kind === 'title') editTitle.value = document.value.title
  if (kind === 'tags') editTags.value = [...(document.value.tags ?? [])]
  if (kind === 'folder') browseFolders([])
}

function closeEditor() {
  edit.value = ''
  folderRequest++
  loadingFolders.value = false
}

async function browseFolders(trail) {
  const id = ++folderRequest
  folderTrail.value = trail
  folderOptions.value = []
  loadingFolders.value = true
  editError.value = ''
  const parent = trail.at(-1)
  const url = parent ? '/api/folders?' + new URLSearchParams({ parent_id: parent.id }) : '/api/folders'
  try {
    const result = await request(url)
    if (id === folderRequest) folderOptions.value = result.folders
  } catch (error) {
    if (id === folderRequest) editError.value = error.message
  } finally {
    if (id === folderRequest) loadingFolders.value = false
  }
}

async function saveEdit() {
  if (saving.value || loadingFolders.value || !edit.value) return
  const kind = edit.value
  const target = endpoint.value
  const trail = folderTrail.value
  const fields = {
    title: { suffix: '', method: 'PATCH', body: { title: editTitle.value.trim() } },
    tags: { suffix: '/tags', method: 'PUT', body: { tags: editTags.value.map(tag => tag.trim()) } },
    folder: { suffix: '/folder', method: 'PUT', body: { folder_id: trail.at(-1)?.id ?? null } },
  }
  const { suffix, method, body } = fields[kind]
  if (kind === 'tags' && body.tags.some(tag => !tag)) {
    editError.value = '请填写每个标签，或移除空白项。'
    return
  }
  saving.value = true
  editError.value = ''
  try {
    await request(target + suffix, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (endpoint.value !== target) return
    closeEditor()
    editNotice.value = kind === 'folder' ? '资料已移动。' : '已保存修改。'
    if (kind === 'folder') {
      await router.replace({ query: { ...route.query, folder: trail.length ? trail.map(folder => folder.id) : undefined } })
    }
    await loadDetail()
  } catch (error) {
    if (endpoint.value === target) editError.value = error.message
  } finally {
    saving.value = false
  }
}

async function request(url, options, readJson = true) {
  const response = await fetch(url, options)
  if (response.status === 401) await router.replace('/login')
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.error || '服务暂时不可用，请稍后重试。')
  }
  if (readJson && response.status !== 204) return response.json()
}

function versionUrl(id) {
  return '/api/versions/' + encodeURIComponent(id)
}

function latestRun(id) {
  return runsByVersion.value[id]?.[0]
}

function isRunning(id) {
  return runsByVersion.value[id]?.some(run => run.status === 'running')
}

async function readRuns(id, page) {
  try {
    const result = await request(versionUrl(id) + '/processing-runs')
    if (disposed || page !== processingPage) return
    runsByVersion.value[id] = result.runs
    delete runErrors.value[id]
  } catch (error) {
    if (disposed || page !== processingPage) return
    runErrors.value[id] = error.message
  }
}

function cancelPolling() {
  clearTimeout(pollTimer)
}

async function refreshRuns() {
  cancelPolling()
  const page = ++processingPage
  const ids = versions.value.map(version => version.id)
  for (let i = 0; i < ids.length; i += 4) {
    await Promise.all(ids.slice(i, i + 4).map(id => readRuns(id, page)))
    if (disposed || page !== processingPage) return
  }
  schedulePoll(page)
}

function schedulePoll(page) {
  if (disposed || page !== processingPage) return
  const active = versions.value.filter(version =>
    isRunning(version.id) || processingVersion.value === version.id,
  ).map(version => version.id)
  if (!active.length) return
  const wasRunning = active.filter(id => isRunning(id))
  pollTimer = setTimeout(async () => {
    await Promise.all(active.map(id => readRuns(id, page)))
    if (disposed || page !== processingPage) return
    if (wasRunning.some(id => !isRunning(id))) {
      await refreshRuns()
    } else {
      schedulePoll(page)
    }
  }, 2000)
}

async function startProcessing(version) {
  if (processingVersion.value || isRunning(version.id)) return
  const target = endpoint.value
  processingVersion.value = version.id
  processError.value = ''
  refreshRuns()
  try {
    await request(versionUrl(version.id) + '/process', { method: 'POST' }, false)
  } catch (error) {
    if (!disposed && endpoint.value === target) processError.value = error.message
  } finally {
    processingVersion.value = null
    if (!disposed && endpoint.value === target) await refreshRuns()
  }
}

onUnmounted(() => {
  disposed = true
  processingPage++
  cancelPolling()
})

async function loadDetail() {
  const id = ++detailRequest
  loading.value = true
  detailError.value = ''
  try {
    const result = await request(endpoint.value)
    if (id === detailRequest) document.value = result
  } catch (error) {
    if (id === detailRequest) detailError.value = error.message
  } finally {
    if (id === detailRequest) loading.value = false
  }
}

async function loadHistory(start = 0) {
  const id = ++historyRequest
  loadingHistory.value = true
  historyError.value = ''
  try {
    const result = await request(endpoint.value + '/versions?limit=' + (PAGE_SIZE + 1) + '&offset=' + start)
    if (id !== historyRequest) return
    versions.value = result.versions.slice(0, PAGE_SIZE)
    offset.value = start
    hasNext.value = result.versions.length > PAGE_SIZE
    refreshRuns()
  } catch (error) {
    if (id === historyRequest) historyError.value = error.message
  } finally {
    if (id === historyRequest) loadingHistory.value = false
  }
}

watch(endpoint, () => {
  processingPage++
  cancelPolling()
  runsByVersion.value = {}
  runErrors.value = {}
  processError.value = ''
  closeEditor()
  confirmingRecycle.value = false
  recycleError.value = ''
  editNotice.value = ''
  document.value = null
  versions.value = []
  offset.value = 0
  hasNext.value = false
  uploadError.value = ''
  uploadOpen.value=false;uploadDirty.value=false
  notice.value = ''
  loadDetail()
  loadHistory()
}, { immediate: true })

async function uploadVersion(event) {
  if (uploading.value) return
  const form = event.currentTarget
  const data = new FormData(form)
  const file = data.get('file')
  const target = endpoint.value
  uploadError.value = ''
  notice.value = ''
  if (!(file instanceof File) || !/\.(txt|md)$/i.test(file.name.trim())) {
    uploadError.value = '请选择 .txt 或 .md 文件。'
    return
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    uploadError.value = '文件大小不能超过 10 MiB。'
    return
  }
  uploading.value = true
  try {
    const result = await request(target + '/versions', { method: 'POST', body: data })
    if (endpoint.value !== target) return
    form.reset()
    uploadDirty.value=false;uploadOpen.value=false
    notice.value = result.created_version
      ? '已上传 v' + result.version_no + '。'
      : '内容与最新版本一致，已复用 v' + result.version_no + '。'
    await Promise.all([loadDetail(), loadHistory()])
  } catch (error) {
    if (endpoint.value === target) uploadError.value = error.message
  } finally {
    uploading.value = false
  }
}

async function recycle() {
  if (recycling.value || !confirmingRecycle.value) return
  const target = endpoint.value
  recycling.value = true
  recycleError.value = ''
  try {
    await request(target, { method: 'DELETE' })
    if (endpoint.value === target) {confirmingRecycle.value=false;await router.replace(libraryLink.value)}
  } catch (error) {
    if (endpoint.value === target) recycleError.value = error.message
  } finally {
    recycling.value = false
  }
}

function localTime(value) {
  return new Date(value).toLocaleString('zh-CN')
}
</script>

<template>
  <main class="detail">
    <RouterLink class="back-link" :to="libraryLink"><AppIcon name="back" :size="15"/>返回资料库</RouterLink>
    <p v-if="loading && !document" role="status">正在读取资料…</p>
    <div v-if="detailError">
      <p role="alert" class="error">{{ detailError }}</p>
      <button type="button" @click="loadDetail">重试详情</button>
    </div>

    <template v-if="document">
      <div class="directory-heading"><div><h1>{{document.title}}</h1><p class="page-description">资料详情 · 原文与处理版本</p></div><button type="button" class="primary" @click="uploadOpen=true;uploadError=''"><AppIcon name="upload" :size="16"/>上传新版本</button></div>


      <section aria-labelledby="organize-title">
        <h2 id="organize-title">资料信息</h2><div class="section-body"><dl class="description-grid"><div><dt>标签</dt><dd><span v-for="tag in document.tags" :key="tag" class="tag">{{tag}}</span><span v-if="!document.tags?.length">未添加标签</span></dd></div><div><dt>更新时间</dt><dd>{{localTime(document.updated_at)}}</dd></div></dl></div>
        <div class="actions">
          <button type="button" :disabled="saving" @click="startEdit('title')">改名</button>
          <button type="button" :disabled="saving" @click="startEdit('tags')">编辑标签</button>
          <button type="button" :disabled="saving" @click="startEdit('folder')">移动目录</button>
        </div>
        <p v-if="editNotice" role="status">{{ editNotice }}</p>

        <WorkOverlay v-if="edit" :kind="edit==='title'?'modal':'drawer'" :title="edit==='title'?'修改资料标题':edit==='tags'?'编辑标签':'移动资料'" :busy="saving" :dirty="editDirty" @close="closeEditor"><form id="document-edit" @submit.prevent="saveEdit">
          <template v-if="edit === 'title'">
            <label for="document-title">资料标题</label>
            <input id="document-title" v-model="editTitle" maxlength="200" required :disabled="saving" />
          </template>

          <template v-else-if="edit === 'tags'">
            <div v-for="(_, index) in editTags" :key="index" class="actions">
              <label :for="'tag-' + index">标签 {{ index + 1 }}</label>
              <input :id="'tag-' + index" v-model="editTags[index]" maxlength="50" required :disabled="saving" />
              <button type="button" :disabled="saving" :aria-label="'移除标签 ' + (index + 1)" @click="editTags.splice(index, 1)">移除</button>
            </div>
            <button type="button" :disabled="saving || editTags.length >= 50" @click="editTags.push('')">添加标签</button>
            <p v-if="!editTags.length">保存后将清空标签。</p>
          </template>

          <template v-else>
            <p>移动到：{{ ['资料库', ...folderTrail.map(folder => folder.name)].join(' / ') }}</p>
            <button v-if="folderTrail.length" type="button" :disabled="saving || loadingFolders" @click="browseFolders(folderTrail.slice(0, -1))">上一级</button>
            <p v-if="loadingFolders" role="status">正在读取文件夹…</p>
            <ul v-else-if="folderOptions.length">
              <li v-for="folder in folderOptions" :key="folder.id">
                <button type="button" :disabled="saving" @click="browseFolders([...folderTrail, folder])">{{ folder.name }} →</button>
              </li>
            </ul>
            <button v-if="editError && !folderOptions.length" type="button" :disabled="saving || loadingFolders" @click="browseFolders(folderTrail)">重新读取文件夹</button>
          </template>

          <p v-if="editError" class="error" role="alert">{{ editError }}</p>
        </form><template #footer="{close}"><button type="button" :disabled="saving" @click="close">取消</button><button type="submit" form="document-edit" class="primary" :disabled="saving||loadingFolders">{{saving?'正在保存…':edit==='folder'?'移到此处':'保存修改'}}</button></template></WorkOverlay>
      </section>



      <WorkOverlay v-if="uploadOpen" title="上传新版本" :description="document.title" :busy="uploading" :dirty="uploadDirty" @close="uploadOpen=false;uploadDirty=false"><form id="version-upload" @submit.prevent="uploadVersion"><div class="upload-drop"><AppIcon name="upload"/><label for="version-file">选择新版本原文</label><input id="version-file" type="file" name="file" accept=".txt,.md" required :disabled="uploading" @change="uploadDirty=!!$event.target.files?.length"/><small>UTF-8 TXT / Markdown · 最大 10 MiB</small></div><p>历史原文将保留。手动处理成功后，检索会使用新版本。</p><p v-if="uploadError" class="error" role="alert">{{uploadError}}</p></form><template #footer="{close}"><button type="button" :disabled="uploading" @click="close">取消</button><button type="submit" form="version-upload" class="primary" :disabled="uploading">{{uploading?'正在上传…':'上传新版本'}}</button></template></WorkOverlay>

      <section aria-labelledby="history-title">
        <h2 id="history-title">版本历史</h2>
        <p v-if="processError" class="error" role="alert">{{ processError }}</p>
        <p v-if="loadingHistory" role="status">正在读取版本…</p>
        <div v-else-if="historyError">
          <p role="alert" class="error">无法读取版本历史。{{ historyError }}</p>
          <button type="button" @click="loadHistory(offset)">重试历史</button>
        </div>
        <template v-else>
          <p v-if="!versions.length">还没有原文版本。</p>
          <ul v-else class="version-history">
            <li v-for="version in versions" :key="version.id">
              <strong>v{{ version.version_no }}</strong>
              <span v-if="version.id === document.latest_version_id" class="latest">最新上传</span>
              <span>{{ localTime(version.captured_at) }}</span>
              <span>{{ version.byte_size.toLocaleString('zh-CN') }} 字节</span>
              <span v-if="runsByVersion[version.id]?.some(run => run.is_published)" class="latest">当前可检索</span>
              <span v-if="processingVersion === version.id || isRunning(version.id)" role="status">处理中…</span>
              <span v-else-if="latestRun(version.id)" role="status">
                {{ processingLabels[latestRun(version.id).status] ?? latestRun(version.id).status }}
                <template v-if="latestRun(version.id).status === 'succeeded'">
                  · {{ latestRun(version.id).chunk_count }} 个片段
                </template>
              </span>
              <span v-else-if="runsByVersion[version.id]">未处理</span>
              <span v-if="latestRun(version.id)?.status === 'failed'" class="error">
                {{ latestRun(version.id).error_summary || '处理失败' }}。同一配置不会自动重试。
              </span>
              <span v-if="runErrors[version.id]" class="error" role="alert">无法读取处理状态：{{ runErrors[version.id] }}</span>
              <button v-if="runErrors[version.id]" type="button" @click="refreshRuns">刷新状态</button>
              <button v-if="runsByVersion[version.id] && latestRun(version.id)?.status !== 'failed'"
                type="button" :disabled="Boolean(processingVersion) || isRunning(version.id)"
                @click="startProcessing(version)">处理</button>
            </li>
          </ul>
          <div v-if="offset || hasNext" class="actions">
            <button type="button" :disabled="!offset" @click="loadHistory(offset - PAGE_SIZE)">上一页</button>
            <button type="button" :disabled="!hasNext" @click="loadHistory(offset + PAGE_SIZE)">下一页</button>
          </div>
        </template>
      </section>

      <div class="detail-recycle"><span>不再需要这份资料？移入回收站后仍可恢复。</span><button type="button" class="ghost" @click="confirmingRecycle=true"><AppIcon name="trash" :size="15"/>移入回收站</button></div>
      <WorkOverlay v-if="confirmingRecycle" kind="modal" title="将资料移入回收站？" :busy="recycling" @close="confirmingRecycle=false;recycleError=''" ><p>「{{document.title}}」将移入回收站，之后可以恢复到原目录。</p><p v-if="recycleError" class="error" role="alert">{{recycleError}}</p><template #footer="{close}"><button type="button" :disabled="recycling" @click="close">取消</button><button type="button" class="danger" :disabled="recycling" @click="recycle">{{recycling?'正在移入…':'移入回收站'}}</button></template></WorkOverlay>
    </template>
  </main>
</template>

