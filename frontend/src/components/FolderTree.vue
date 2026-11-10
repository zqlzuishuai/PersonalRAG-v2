<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import FolderTreeNode from './FolderTreeNode.vue'
import AppIcon from './AppIcon.vue'

const props=defineProps({path:{type:Array,default:()=>[]},fetchChildren:{type:Function,required:true},revision:Number})
const emit=defineEmits(['rename','move','recycle'])
const roots=ref([]),loading=ref(false),error=ref(''),revision=ref(0),loaded=ref(false)
let requestId=0
async function refresh(){
  const id=++requestId
  loading.value=true;error.value=''
  try{
    const result=await props.fetchChildren(null)
    if(id!==requestId)return
    roots.value=result;loaded.value=true;revision.value++
  }catch(cause){if(id===requestId)error.value=cause.message}
  finally{if(id===requestId)loading.value=false}
}
watch(()=>props.revision,refresh,{immediate:true})
onBeforeUnmount(()=>{requestId++})
</script>
<template>
  <nav class="folder-tree" aria-label="文件夹目录" :aria-busy="loading">
    <RouterLink class="tree-root" :class="{'is-current':!path.length}" to="/library" :aria-current="!path.length?'page':undefined"><AppIcon name="library" :size="16"/><span>全部资料</span></RouterLink>
    <div v-if="loading&&!loaded" class="tree-loading" role="status"><span class="sr-only">正在读取目录…</span><div v-for="row in 3" :key="row" class="tree-loading-row" aria-hidden="true"><span></span><i></i></div></div>
    <div v-if="error" class="tree-message tree-error" role="alert"><span>{{error}}</span><button type="button" @click="refresh">重试</button></div>
    <p v-else-if="loaded&&!roots.length" class="tree-message">还没有文件夹。</p>
    <ul v-if="roots.length" class="tree-branches">
      <FolderTreeNode v-for="folder in roots" :key="folder.id" :folder="folder" :ancestors="[]" :active-path="path" :fetch-children="fetchChildren" :revision="revision" @rename="emit('rename',$event)" @move="emit('move',$event)" @recycle="emit('recycle',$event)"/>
    </ul>
  </nav>
</template>
