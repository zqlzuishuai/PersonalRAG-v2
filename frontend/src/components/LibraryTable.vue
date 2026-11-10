<script setup>
import { h, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { NButton, NDataTable, NEmpty, NTag } from 'naive-ui'
import AppIcon from './AppIcon.vue'

const props=defineProps({documents:{type:Array,required:true},query:Object})
const emit=defineEmits(['preview','clear'])
const columns=computed(()=>[
  {title:'资料名称',key:'title',minWidth:260,render:document=>h('div',{class:'desk-document'},[
    h('span',{class:'desk-file'},h(AppIcon,{name:'file',size:19})),
    h(NButton,{text:true,class:'desk-document-open',onClick:()=>emit('preview',document)},{default:()=>document.title}),
  ])},
  {title:'标签',key:'tags',width:190,render:document=>document.tags?.length
    ?h('div',{class:'desk-tags'},document.tags.map(tag=>h(NTag,{size:'small',round:true,bordered:false},{default:()=>tag})))
    :h('span',{class:'desk-muted'},'—')},
  {title:'更新时间',key:'updated_at',width:132,render:document=>document.updated_at
    ?h('time',{datetime:document.updated_at},new Date(document.updated_at).toLocaleDateString('zh-CN')):'—'},
  {title:'',key:'actions',width:96,render:document=>h(RouterLink,{
    to:{name:'document',params:{documentId:document.id},query:props.query},custom:true,
  },{default:({href,navigate})=>h(NButton,{tag:'a',href,text:true,class:'desk-detail',onClick:navigate,'aria-label':'管理版本 '+document.title},{default:()=>'管理版本'})})},
])
</script>
<template>
  <NDataTable class="desk-table" :columns="columns" :data="documents" :row-key="document=>document.id" :bordered="false" :single-line="true" :scroll-x="700" :min-height="280">
    <template #empty><NEmpty description="没有符合当前条件的资料"><template #extra><NButton size="small" @click="emit('clear')">清除筛选</NButton></template></NEmpty></template>
  </NDataTable>
</template>
