<script setup>
import { computed, ref, watch, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import WorkOverlay from '../components/WorkOverlay.vue'
import FolderTree from '../components/FolderTree.vue'
import LibraryTable from '../components/LibraryTable.vue'
import LibrarySkeleton from '../components/LibrarySkeleton.vue'
import { createFolderCache } from '../data/folderCache.js'
import { NConfigProvider, NButton, NInput, NSelect, NTag, NAlert, NEmpty } from 'naive-ui'

const libraryTheme={
  common:{primaryColor:'#326b50',primaryColorHover:'#28563f',primaryColorPressed:'#204632',primaryColorSuppl:'#326b50',textColorBase:'#23352c',textColor2:'#627369',borderColor:'#dce5df',borderRadius:'6px',fontFamily:"'Microsoft YaHei','PingFang SC',system-ui,sans-serif",fontSize:'14px',heightMedium:'38px'},
  Button:{fontWeight:'500'},
  DataTable:{thColor:'#f7f9f7',thTextColor:'#627369',thFontWeight:'500',tdColorHover:'#f5f9f6',tdPaddingMedium:'20px',thPaddingMedium:'12px 20px',borderColor:'#e8ede9'},
  Tag:{color:'#f0f5f1',textColor:'#476454',borderRadius:'4px'},
}

const route = useRoute()
const router = useRouter()

const folderPath = computed(() => [route.query.folder].flat().filter(Boolean))
const currentFolder = computed(() => folderPath.value.at(-1) ?? null)
const breadcrumbs = ref([])
const folders = ref([])
const documents = ref([])
const foldersInline = inject('workspaceFoldersInline', true)
const pageTags = computed(() => [...new Set(documents.value.flatMap(item => item.tags ?? []))])
const loading = ref(true)
const loadError = ref('')
const hasContent = ref(false),requestedKey = ref(''),displayedKey = ref('')
const refreshingContent = computed(() => loading.value&&hasContent.value&&requestedKey.value===displayedKey.value)
const folderRevision = ref(0)
const editor = ref(null)
const uploadOpen=ref(false),uploadDirty=ref(false)
const peek=ref(null),peekVersions=ref([]),peekLoading=ref(false),peekError=ref('')
let peekRequest=0
async function quickView(item){
  const previewRequest=++peekRequest
  peek.value=item;peekVersions.value=[];peekError.value='';peekLoading.value=true
  try{const result=await request('/api/documents/'+encodeURIComponent(item.id)+'/versions?limit=5&offset=0');if(peek.value&&previewRequest===peekRequest)peekVersions.value=result.versions}
  catch(error){if(peek.value&&previewRequest===peekRequest)peekError.value=error.message}
  finally{if(peek.value&&previewRequest===peekRequest)peekLoading.value=false}
}
const moving = ref(null)
const moveNotice = ref('')
const recycleTarget = ref(null)
const recycling = ref(false)
const recycleError = ref('')
const recycleNotice = ref('')
const name = ref('')
const saveError = ref('')
const saving = ref(false)
const uploading = ref(false)
const uploadError = ref('')
const uploadNotice = ref('')
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024
const PAGE_SIZE = 20
const hasNextPage = ref(false)
const offset = ref(0)
const scope = ref('folder')
const titleQuery = ref('')
const tagQuery = ref('')
const selectedTags = computed(() => [...new Set(tagQuery.value.split(/\r?\n/).map(tag => tag.trim()).filter(Boolean))])
const knownTags = ref([])
const tagOptions = computed(() => [...new Set([...knownTags.value,...selectedTags.value])].map(tag => ({label:tag,value:tag})))
watch(pageTags,tags=>{knownTags.value=[...new Set([...knownTags.value,...tags])]},{immediate:true})
function selectTags(tags) {
  tagQuery.value = [...new Set((tags??[]).map(tag=>tag.trim()).filter(Boolean))].join('\n')
  applyFilters()
}
const filters = ref({ scope: 'folder', q: '', tags: [] })
const filterError = ref('')
let loadId = 0
const folderCache = createFolderCache(async parentId => (await request(listUrl('folders','parent_id',parentId))).folders)
function invalidateFolders() { folderCache.clear();folderRevision.value++ }
function refreshDirectory() { invalidateFolders();return loadDirectory(folderPath.value) }

function location(path) {
  return { path: '/library', query: path.length ? { folder: path } : {} }
}

function listUrl(resource, parameter, id) {
  return id ? '/api/' + resource + '?' + new URLSearchParams({ [parameter]: id }) : '/api/' + resource
}

async function request(url, options) {
  const response = await fetch(url, options)
  if (response.status === 401) {
    await router.replace('/login')
    throw new Error('登录已失效，请重新登录。')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.error || '服务暂时不可用，请稍后重试。')
  }
  if (response.status !== 204) return response.json()
}

async function fetchFolders(parentId) {
  return folderCache.load(parentId)
}

function documentUrl(parentId) {
  const { scope, q, tags } = filters.value
  const params = new URLSearchParams({ scope, limit: String(PAGE_SIZE + 1), offset: String(offset.value) })
  if (parentId && scope !== 'all') params.set('folder_id', parentId)
  if (q) params.set('q', q)
  for (const tag of tags) params.append('tag', tag)
  return '/api/documents?' + params
}

function applyFilters() {
  const tags = [...new Set(tagQuery.value.split(/\r?\n/).map(tag => tag.trim()).filter(Boolean))]
  if (tags.some(tag => [...tag].length > 50)) {
    filterError.value = '每个标签最多 50 个字符。'
    return
  }
  filterError.value = ''
  filters.value = { scope: scope.value, q: titleQuery.value.trim(), tags }
  offset.value = 0
  loadDirectory(folderPath.value)
}

function clearFilters() {
  scope.value = 'folder'
  titleQuery.value = ''
  tagQuery.value = ''
  applyFilters()
}

function changePage(step) {
  const next = offset.value + step * PAGE_SIZE
  if (next < 0 || (step > 0 && !hasNextPage.value)) return
  offset.value = next
  loadDirectory(folderPath.value)
}

async function loadDirectory(path) {
  const id = ++loadId
  const key = JSON.stringify([path,filters.value,offset.value])
  const keepContent = hasContent.value&&displayedKey.value===key
  requestedKey.value = key
  loading.value = true
  loadError.value = ''
  if (!keepContent) {
    hasContent.value=false
    breadcrumbs.value=[];folders.value=[];documents.value=[]
  }
  try {
    const trail = []
    let parentId = null
    for (const folderId of path) {
      const siblings = await fetchFolders(parentId)
      if (id !== loadId) return
      const folder = siblings.find((item) => item.id === folderId)
      if (!folder) throw new Error('找不到这个目录。请返回资料库首页。')
      trail.push(folder)
      parentId = folder.id
    }
    const [children, result] = await Promise.all([
      fetchFolders(parentId),
      request(documentUrl(parentId)),
    ])
    if (id !== loadId) return
    breadcrumbs.value = trail
    folders.value = children
    documents.value = result.documents.slice(0, PAGE_SIZE)
    hasNextPage.value = result.documents.length > PAGE_SIZE
    displayedKey.value=key;hasContent.value=true
  } catch (error) {
    if (id === loadId) loadError.value = error.message
  } finally {
    if (id === loadId) loading.value = false
  }
}

watch(folderPath, (path) => {
  recycleTarget.value = null
  recycleError.value = ''
  recycleNotice.value = ''
  offset.value = 0
  if (!path.length && scope.value === 'subtree') scope.value = 'folder'
  if (!path.length && filters.value.scope === 'subtree') filters.value = { ...filters.value, scope: 'folder' }
  editor.value = null
  uploadOpen.value=false;uploadDirty.value=false;peek.value=null
  uploadError.value = ''
  uploadNotice.value = ''
  moving.value = null
  moveNotice.value = ''
  loadDirectory(path)
}, { immediate: true })

function editFolder(folder = null) {
  if (recycling.value) return
  recycleTarget.value = null
  moving.value = null
  editor.value = { folder }
  name.value = folder?.name ?? ''
  saveError.value = ''
}

async function saveFolder() {
  if (saving.value || !editor.value) return
  const editing = editor.value
  const folderName = name.value.trim()
  if (!folderName) {
    saveError.value = '请输入文件夹名称。'
    return
  }
  const target = editing.folder
  const path = folderPath.value
  const parentId = currentFolder.value
  saving.value = true
  saveError.value = ''
  try {
    await request(target ? '/api/folders/' + encodeURIComponent(target.id) : '/api/folders', {
      method: target ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(target ? { name: folderName } : { name: folderName, parent_id: parentId }),
    })
    invalidateFolders()
    if (editor.value === editing) editor.value = null
    if (folderPath.value === path) await loadDirectory(path)
  } catch (error) {
    if (editor.value === editing) saveError.value = error.message
  } finally {
    saving.value = false
  }
}

async function browseMoveTargets(trail) {
  const move = moving.value
  if (!move || move.loading || move.saving) return
  move.loading = true
  move.error = ''
  move.trail = trail
  move.children = []
  try {
    const children = await fetchFolders(trail.at(-1)?.id ?? null)
    move.children = children.filter(folder => folder.id !== move.folder.id)
  } catch (error) {
    move.error = error.message
  } finally {
    move.loading = false
  }
}

function startFolderMove(folder) {
  if (recycling.value) return
  recycleTarget.value = null
  editor.value = null
  moveNotice.value = ''
  moving.value = { folder, trail: [], children: [], loading: false, saving: false, error: '' }
  browseMoveTargets([])
}

async function submitFolderMove() {
  const move = moving.value
  if (!move || move.loading || move.saving) return
  const path = folderPath.value
  move.saving = true
  move.error = ''
  try {
    await request('/api/folders/' + encodeURIComponent(move.folder.id) + '/parent', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ parent_id: move.trail.at(-1)?.id ?? null }),
    })
    invalidateFolders()
    if (moving.value === move) {
      moving.value = null
      moveNotice.value = '已移动「' + move.folder.name + '」。'
    }
    if (folderPath.value === path) await loadDirectory(path)
  } catch (error) {
    move.error = error.message
  } finally {
    move.saving = false
  }
}

function startFolderRecycle(folder) {
  editor.value = null
  moving.value = null
  recycleTarget.value = folder
  recycleError.value = ''
  recycleNotice.value = ''
}

async function recycleFolder() {
  if (recycling.value || !recycleTarget.value) return
  const target = recycleTarget.value
  const path = folderPath.value
  recycling.value = true
  recycleError.value = ''
  try {
    await request('/api/folders/' + encodeURIComponent(target.id), { method: 'DELETE' })
    invalidateFolders()
    if (folderPath.value === path) {
      recycleTarget.value = null
      recycleNotice.value = '已将「' + target.name + '」及其内容移入回收站。'
      offset.value = 0
      await loadDirectory(path)
    }
  } catch (error) {
    if (folderPath.value === path) recycleError.value = error.message
  } finally {
    recycling.value = false
  }
}

async function uploadDocument(event) {
  if (uploading.value) return
  const form = event.currentTarget
  const data = new FormData(form)
  const file = data.get('file')
  const path = folderPath.value
  uploadError.value = ''
  uploadNotice.value = ''
  if (!(file instanceof File) || !/\.(txt|md)$/i.test(file.name.trim())) {
    uploadError.value = '请选择 .txt 或 .md 文件。'
    return
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    uploadError.value = '文件大小不能超过 10 MiB。'
    return
  }
  data.set('folder_id', currentFolder.value ?? '')
  uploading.value = true
  try {
    await request('/api/documents', { method: 'POST', body: data })
    if (folderPath.value === path) {
      form.reset()
      uploadDirty.value=false;uploadOpen.value=false
      uploadNotice.value = '文件已上传到当前目录。'
      offset.value = 0
      await loadDirectory(path)
    }
  } catch (error) {
    if (folderPath.value === path) uploadError.value = error.message
  } finally {
    uploading.value = false
  }
}

</script>

<template>
  <NConfigProvider tag="main" class="library library-list-layout library-naive" :theme-overrides="libraryTheme" preflight-style-disabled>
    <header class="library-header">
    <Teleport defer to="#workspace-breadcrumbs"><nav aria-label="当前位置" class="breadcrumbs"><RouterLink :to="location([])">资料库</RouterLink><template v-for="(folder,index) in breadcrumbs" :key="folder.id"><AppIcon name="chevron" :size="12"/><RouterLink v-if="index<breadcrumbs.length-1" :to="location(folderPath.slice(0,index+1))">{{folder.name}}</RouterLink><span v-else aria-current="page">{{folder.name}}</span></template></nav></Teleport>
    <div class="directory-heading"><div><h1>{{breadcrumbs.at(-1)?.name ?? '我的资料'}}</h1><p class="page-description">按目录整理资料，查看原文与版本。</p></div></div>
    <Teleport defer to="#workspace-actions"><div class="heading-actions library-naive naive-actions"><NButton :disabled="loading||!!loadError" @click="editFolder()"><template #icon><AppIcon name="plus" :size="16"/></template>新建文件夹</NButton><NButton type="primary" :disabled="loading||!!loadError" @click="uploadOpen=true;uploadError='' "><template #icon><AppIcon name="upload" :size="16"/></template>上传资料</NButton></div></Teleport>
    </header>
    <div class="desk-overview" aria-label="当前列表概览"><span><strong>{{hasContent?documents.length:'—'}}</strong> 本页资料</span><span><strong>{{hasContent?folders.length:'—'}}</strong> 子文件夹</span><span><strong>{{hasContent?pageTags.length:'—'}}</strong> 本页标签</span></div>
    <NAlert v-if="moveNotice||recycleNotice||uploadNotice" class="desk-notice" type="success" :show-icon="false">{{moveNotice||recycleNotice||uploadNotice}}</NAlert>
    <Teleport defer to="#workspace-folders" :disabled="foldersInline">
    <section class="data-section library-folders" aria-labelledby="folders-title">
      <div class="section-toolbar"><div><span class="section-eyebrow">当前目录</span><h2 id="folders-title">文件夹</h2></div></div>
      <FolderTree :path="folderPath" :fetch-children="fetchFolders" :revision="folderRevision" @rename="editFolder" @move="startFolderMove" @recycle="startFolderRecycle" />
    </section>
    </Teleport>
    <section class="desk-surface" aria-labelledby="documents-title">
    <div class="desk-toolbar"><div class="desk-list-heading"><h2 id="documents-title">资料列表</h2><NTag size="small" round :bordered="false">{{hasContent?documents.length+' 份':'读取中'}}</NTag></div><NButton quaternary size="small" :disabled="loading" :loading="refreshingContent" aria-label="刷新资料" @click="refreshDirectory"><template #icon><AppIcon name="refresh" :size="15"/></template>{{refreshingContent?'刷新中':'刷新'}}</NButton></div>
    <form class="desk-filters" @submit.prevent="applyFilters">
      <div class="desk-filter-row">
        <NInput v-model:value="titleQuery" clearable placeholder="搜索资料标题" :input-props="{id:'document-query','aria-label':'标题关键词'}"><template #prefix><AppIcon name="search" :size="17"/></template></NInput>
        <NSelect v-model:value="scope" class="desk-scope" aria-label="筛选范围" :options="[{label:'当前目录',value:'folder'},...(currentFolder?[{label:'包含子目录',value:'subtree'}]:[]),{label:'全部资料',value:'all'}]" :input-props="{'aria-label':'筛选范围'}" :menu-props="{class:'library-naive-popup'}"/>
        <NButton type="primary" attr-type="submit" aria-label="筛选资料">搜索</NButton>
        <NButton quaternary @click="clearFilters">重置</NButton>
      </div>
      <div class="desk-tag-row"><label for="document-tags">标签筛选</label><div class="desk-tag-control"><NSelect :value="selectedTags" :options="tagOptions" multiple filterable tag clearable :max-tag-count="3" :theme-overrides="{peers:{InternalSelectMenu:{height:'min(220px, 40dvh)'}}}" placeholder="选择或输入标签" :input-props="{id:'document-tags','aria-label':'标签筛选','aria-describedby':'tag-filter-hint'}" :menu-props="{class:'library-naive-popup'}" @update:value="selectTags"><template #action><span class="desk-tag-menu-hint">输入其他标签后按 Enter 添加</span></template></NSelect><span id="tag-filter-hint" class="desk-tag-hint">候选来自已浏览资料；多个标签同时匹配。</span></div></div>
      <p v-if="filterError" class="error" role="alert">{{filterError}}</p>
      <Transition name="filter-tags"><div v-if="filters.q" class="filter-tags-region"><div class="filter-tags-clip"><div class="filter-tags"><NTag v-if="filters.q" size="small">标题：{{filters.q}}</NTag><NButton text size="tiny" @click="clearFilters">清除筛选</NButton></div></div></div></Transition>
    </form>
    <NAlert v-if="loadError&&hasContent" class="desk-refresh-error" type="warning" :show-icon="false">刷新失败，保留上次结果：{{loadError}}</NAlert>
    <div class="state-region desk-content" :aria-busy="loading">
      <Transition name="state">
        <LibrarySkeleton v-if="loading&&!refreshingContent" key="loading"/>
        <div v-else-if="loadError&&!hasContent" key="error" class="desk-error" role="alert"><NEmpty :description="loadError"><template #extra><NButton @click="loadDirectory(folderPath)">重新读取</NButton></template></NEmpty></div>
        <LibraryTable v-else key="content" :documents="documents" :query="route.query" @preview="quickView" @clear="clearFilters"/>
      </Transition>
    </div>
    <nav class="desk-pagination" aria-label="资料分页"><span>每页 {{PAGE_SIZE}} 份 · 本页 {{documents.length}} 份</span><div><NButton size="small" :disabled="loading||offset===0" @click="changePage(-1)"><template #icon><AppIcon name="back" :size="14"/></template>上一页</NButton><span class="desk-page-number" aria-current="page">{{offset/PAGE_SIZE+1}}</span><NButton size="small" :disabled="loading||!hasNextPage" @click="changePage(1)">下一页<template #icon><AppIcon name="chevron" :size="14"/></template></NButton></div></nav>
    </section>
    <WorkOverlay v-if="editor" kind="modal" :title="editor.folder?'重命名文件夹':'新建文件夹'" :busy="saving" :dirty="name!==(editor.folder?.name??'')" @close="editor=null"><form id="folder-form" @submit.prevent="saveFolder"><div class="field"><label for="folder-name">文件夹名称</label><input id="folder-name" v-model="name" maxlength="200" required :disabled="saving"/></div><p v-if="saveError" class="error" role="alert">{{saveError}}</p></form><template #footer="{close}"><button type="button" :disabled="saving" @click="close">取消</button><button type="submit" form="folder-form" class="primary" :disabled="saving">{{saving?'正在保存…':'保存文件夹'}}</button></template></WorkOverlay>
    <WorkOverlay v-if="uploadOpen" title="上传新资料" description="上传到当前目录，同名文件会创建独立资料。" :busy="uploading" :dirty="uploadDirty" @close="uploadOpen=false;uploadDirty=false"><form id="upload-form" @submit.prevent="uploadDocument"><div class="upload-drop"><AppIcon name="upload"/><label for="upload-file">选择原文文件</label><input id="upload-file" name="file" type="file" accept=".txt,.md" required :disabled="uploading" @change="uploadDirty=!!$event.target.files?.length"/><small>UTF-8 TXT / Markdown · 最大 10 MiB</small></div><p>上传后，在版本详情中手动处理即可检索正文。</p><p v-if="uploadError" class="error" role="alert">{{uploadError}}</p></form><template #footer="{close}"><button type="button" :disabled="uploading" @click="close">取消</button><button type="submit" form="upload-form" class="primary" :disabled="uploading">{{uploading?'正在上传…':'上传文件'}}</button></template></WorkOverlay>
    <WorkOverlay v-if="moving" title="移动文件夹" :description="moving.folder.name" :busy="moving.saving" :dirty="moving.trail.length>0" @close="moving=null"><form id="folder-move" @submit.prevent="submitFolderMove"><p>目标：{{['资料库',...moving.trail.map(folder=>folder.name)].join(' / ')}}</p><button v-if="moving.trail.length" type="button" :disabled="moving.loading||moving.saving" @click="browseMoveTargets(moving.trail.slice(0,-1))">上一级</button><p v-if="moving.loading" role="status">正在读取文件夹…</p><ul v-else><li v-for="folder in moving.children" :key="folder.id"><button type="button" @click="browseMoveTargets([...moving.trail,folder])">{{folder.name}}<AppIcon name="chevron" :size="16"/></button></li></ul><p v-if="!moving.loading&&!moving.children.length" class="empty">此目录没有可选的子文件夹。</p><p v-if="moving.error" class="error" role="alert">{{moving.error}}</p></form><template #footer="{close}"><button type="button" :disabled="moving.saving" @click="close">取消</button><button type="submit" form="folder-move" class="primary" :disabled="moving.loading||moving.saving">{{moving.saving?'正在移动…':'移到此处'}}</button></template></WorkOverlay>
    <WorkOverlay v-if="recycleTarget" kind="modal" title="将文件夹移入回收站？" :busy="recycling" @close="recycleTarget=null"><p>「{{recycleTarget.name}}」及其子目录和资料将一起移入回收站。之后可以恢复同批回收的内容。</p><p v-if="recycleError" class="error" role="alert">{{recycleError}}</p><template #footer="{close}"><button type="button" :disabled="recycling" @click="close">取消</button><button type="button" class="danger" :disabled="recycling" @click="recycleFolder">{{recycling?'正在回收…':'移入回收站'}}</button></template></WorkOverlay>
    <WorkOverlay v-if="peek" title="资料速览" @close="peek=null"><div class="preview-title"><AppIcon name="file"/><h3>{{peek.title}}</h3></div><dl class="description-grid"><div><dt>标签</dt><dd><span v-for="tag in peek.tags" :key="tag" class="tag">{{tag}}</span><span v-if="!peek.tags?.length">未添加标签</span></dd></div><div><dt>更新时间</dt><dd>{{new Date(peek.updated_at).toLocaleString('zh-CN')}}</dd></div></dl><div class="preview-section"><h3>最近版本</h3><p v-if="peekLoading" role="status">正在读取版本…</p><div v-else-if="peekError"><p class="error" role="alert">{{peekError}}</p><button type="button" @click="quickView(peek)">重新读取</button></div><ul v-else><li v-for="version in peekVersions" :key="version.id" class="version-mini"><span>v{{version.version_no}} <span v-if="version.id===peek.latest_version_id" class="badge">最新上传</span></span><small>{{version.byte_size.toLocaleString('zh-CN')}} 字节</small></li><li v-if="!peekVersions.length" class="empty">尚无原文版本。</li></ul></div><template #footer="{close}"><button type="button" @click="close">关闭</button><RouterLink class="button-link primary" :to="{name:'document',params:{documentId:peek.id},query:route.query}">打开完整详情 <AppIcon name="external" :size="15"/></RouterLink></template></WorkOverlay>
  </NConfigProvider>
</template>
