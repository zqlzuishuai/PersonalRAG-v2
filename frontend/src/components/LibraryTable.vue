<script setup>
import { h, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { NButton, NDataTable, NTag } from 'naive-ui'
import AppIcon from './AppIcon.vue'

const props = defineProps({ documents: { type: Array, required: true }, query: Object, compact: Boolean })
const emit = defineEmits(['preview'])
const detailsRoute = (document) => ({ name: 'document', params: { documentId: document.id }, query: props.query })
const formatDate = (value) => new Date(value).toLocaleDateString('zh-CN')
const columns=computed(()=>[
  {title:'资料名称',key:'title',minWidth:260,render:document=>h('div',{class:'desk-document'},[
    h('span',{class:'desk-file'},h(AppIcon,{name:'file',size:19})),
    h(NButton,{text:true,class:'desk-document-open',onClick:()=>emit('preview',document)},{default:()=>document.title}),
  ])},
  {title:'标签',key:'tags',width:190,render:document=>document.tags?.length
    ?h('div',{class:'desk-tags'},document.tags.map(tag=>h(NTag,{size:'small',round:true,bordered:false},{default:()=>tag})))
    :h('span',{class:'desk-muted'},'—')},
  {title:'更新时间',key:'updated_at',width:132,render:document=>document.updated_at
    ?h('time',{datetime:document.updated_at},formatDate(document.updated_at)):'—'},
  {title:'',key:'actions',width:96,render:document=>h(RouterLink,{
    to:detailsRoute(document),custom:true,
  },{default:({href,navigate})=>h(NButton,{tag:'a',href,text:true,class:'desk-detail',onClick:navigate,'aria-label':'管理版本 '+document.title},{default:()=>'管理版本'})})},
])
</script>
<template>
  <ul v-if="compact" class="desk-document-list">
    <li v-for="document in documents" :key="document.id" class="desk-document-row">
      <button type="button" class="desk-mobile-title" @click="emit('preview', document)">
        <span class="desk-file"><AppIcon name="file" :size="17"/></span>
        <span>{{ document.title }}</span>
      </button>
      <RouterLink class="desk-mobile-detail" :to="detailsRoute(document)" :aria-label="'管理版本 ' + document.title">管理版本</RouterLink>
      <div v-if="document.updated_at || document.tags?.length" class="desk-mobile-meta">
        <time v-if="document.updated_at" :datetime="document.updated_at">{{ formatDate(document.updated_at) }} 更新</time>
        <ul v-if="document.tags?.length" class="desk-tags" aria-label="标签">
          <li v-for="tag in document.tags" :key="tag"><NTag size="small" round :bordered="false">{{ tag }}</NTag></li>
        </ul>
      </div>
    </li>
  </ul>
  <NDataTable v-else class="desk-table" :columns="columns" :data="documents" :row-key="document=>document.id" :bordered="false" :single-line="true" :scroll-x="700" :min-height="280"/>
</template>
