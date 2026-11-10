<script setup>
import { onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const query = ref('')
const topK = ref(5)
const results = ref([])
const loading = ref(false)
const searched = ref(false)
const error = ref('')
const submittedQuery = ref('')
let controller

async function search() {
  if (loading.value) return
  const text = query.value.trim()
  error.value = ''
  if (!text || !Number.isInteger(topK.value) || topK.value < 1 || topK.value > 20) {
    error.value = '请输入检索内容，结果数量须为 1 到 20 的整数。'
    return
  }
  results.value = []
  searched.value = false
  submittedQuery.value = text
  loading.value = true
  controller = new AbortController()
  const signal = controller.signal
  try {
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: text, top_k: topK.value }),
      signal,
    })
    if (response.status === 401) {
      await router.replace('/login')
      return
    }
    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(payload?.error || '搜索暂时不可用，请稍后重试。')
    }
    const payload = await response.json()
    if (signal.aborted) return
    results.value = payload.results
    searched.value = true
  } catch (failure) {
    if (!signal.aborted) error.value = failure.message
  } finally {
    if (!signal.aborted) loading.value = false
  }
}

onUnmounted(() => controller?.abort())
</script>

<template>
  <main class="search-page">
    <div class="page-heading"><h1>正文检索</h1><p class="page-description">描述你要找的内容，检索已处理的原文片段。</p></div>
    <form class="search-form" @submit.prevent="search">
      <label for="content-query">查找已处理资料中的内容</label>
      <textarea id="content-query" v-model="query" rows="3" placeholder="你想从资料中找到什么？" required :disabled="loading"></textarea>
      <div class="actions">
        <label for="result-count">结果数量</label>
        <input id="result-count" v-model.number="topK" type="number" min="1" max="20" step="1" required :disabled="loading" />
        <button class="primary" type="submit" :disabled="loading">{{ loading ? '正在检索…' : '检索正文' }}</button>
      </div>
    </form>
    <div class="state-region documents-state" :aria-busy="loading">
      <Transition name="state">
        <div v-if="loading" key="loading" class="search-skeleton" role="status"><span class="sr-only">正在查找相关片段…</span><div v-for="row in 3" :key="row" class="search-skeleton-row" aria-hidden="true"><span class="skeleton-line skeleton-short"></span><span class="skeleton-line"></span></div></div>
        <p v-else-if="error" key="error" class="error" role="alert">{{error}}</p>
        <div v-else-if="!searched" key="guide" class="search-guide"><h2>从原文出发</h2><p>结果将保留资料标题、版本和命中片段，方便你回到来源。</p><small>还没有结果？请先在资料详情中处理上传的版本。</small></div>
        <div v-else-if="!results.length" key="empty" class="empty"><p role="status">「{{submittedQuery}}」找到 0 个片段。</p><p>没有找到片段。可以换个描述，或先在资料详情中处理原文。</p></div>
        <div v-else key="content">
          <p role="status">「{{submittedQuery}}」找到 {{results.length}} 个片段。</p>
          <TransitionGroup name="list-item" tag="ol" appear>
            <li v-for="result in results" :key="result.chunk_id"><article><h2><RouterLink :to="{ name: 'document', params: { documentId: result.document_id } }">{{result.title}}</RouterLink></h2><p class="source">v{{result.version_no}}<span v-if="Number.isInteger(result.locator?.ordinal)"> · 片段 {{result.locator.ordinal + 1}}</span></p><p class="content">{{result.content}}</p></article></li>
          </TransitionGroup>
        </div>
      </Transition>
    </div>
  </main>
</template>

