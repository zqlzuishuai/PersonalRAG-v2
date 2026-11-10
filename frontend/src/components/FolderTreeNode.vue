<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import AppIcon from './AppIcon.vue'
import { DropdownMenuRoot, DropdownMenuTrigger, DropdownMenuPortal, DropdownMenuContent, DropdownMenuItem } from 'reka-ui'

const props=defineProps({folder:{type:Object,required:true},ancestors:{type:Array,required:true},activePath:{type:Array,required:true},fetchChildren:{type:Function,required:true},revision:Number})
const emit=defineEmits(['rename','move','recycle'])
const expanded=ref(false),children=ref(null),loading=ref(false),error=ref('')
const path=computed(()=>[...props.ancestors,props.folder.id])
const selected=computed(()=>props.activePath.at(-1)===props.folder.id)
const menuTrigger=ref(null)
let pendingAction=null
function selectAction(action){pendingAction={action,folder:props.folder}}
function finishMenuClose(event){
  if(!pendingAction)return
  event.preventDefault()
  menuTrigger.value?.focus()
  const {action,folder}=pendingAction
  pendingAction=null
  emit(action,folder)
}
let requestId=0
async function load(){
  const id=++requestId
  loading.value=true;error.value=''
  try{
    const result=await props.fetchChildren(props.folder.id)
    if(id!==requestId)return
    children.value=result
  }catch(cause){if(id===requestId)error.value=cause.message}
  finally{if(id===requestId)loading.value=false}
}
function toggle(){expanded.value=!expanded.value;if(expanded.value&&children.value===null&&!loading.value)load()}
watch([()=>props.revision,()=>props.activePath.join('/')],()=>{
  if(props.activePath.includes(props.folder.id))expanded.value=true
  if(expanded.value)load()
},{immediate:true})
onBeforeUnmount(()=>{requestId++})
</script>
<template>
  <li class="tree-node" :aria-busy="loading">
    <div class="tree-row" :class="{'is-current':selected}">
      <button type="button" class="tree-disclosure" :aria-label="(expanded?'收起 ':'展开 ')+folder.name" :aria-expanded="expanded" @click="toggle"><AppIcon name="chevron" :size="14"/></button>
      <RouterLink class="tree-link" :to="{path:'/library',query:{folder:path}}" :title="folder.name" :aria-current="selected?'page':undefined"><AppIcon name="folder" :size="16"/><span>{{folder.name}}</span></RouterLink>
      <DropdownMenuRoot :modal="false">
        <DropdownMenuTrigger as-child><button ref="menuTrigger" type="button" class="tree-menu-trigger" :aria-label="'管理 '+folder.name" :title="'管理 '+folder.name">···</button></DropdownMenuTrigger>
        <DropdownMenuPortal><DropdownMenuContent class="tree-menu" align="end" :side-offset="4" :collision-padding="8" @close-auto-focus="finishMenuClose">
          <DropdownMenuItem :aria-label="'重命名 '+folder.name" @select="selectAction('rename')">改名</DropdownMenuItem>
          <DropdownMenuItem :aria-label="'移动 '+folder.name" @select="selectAction('move')">移动</DropdownMenuItem>
          <DropdownMenuItem class="tree-recycle" :aria-label="'回收 '+folder.name" @select="selectAction('recycle')">回收</DropdownMenuItem>
        </DropdownMenuContent></DropdownMenuPortal>
      </DropdownMenuRoot>
    </div>

    <template v-if="expanded">
      <div v-if="loading&&children===null" class="tree-loading tree-child-loading" role="status"><span class="sr-only">正在读取子目录…</span><div class="tree-loading-row" aria-hidden="true"><span></span><i></i></div></div>
      <div v-if="error" class="tree-message tree-error" role="alert"><span>{{error}}</span><button type="button" @click="load">重试</button></div>
      <ul v-if="children?.length" class="tree-branches">
        <FolderTreeNode v-for="child in children" :key="child.id" :folder="child" :ancestors="path" :active-path="activePath" :fetch-children="fetchChildren" :revision="revision" @rename="emit('rename',$event)" @move="emit('move',$event)" @recycle="emit('recycle',$event)"/>
      </ul>
      <p v-else-if="children&&!loading&&!error" class="tree-message">没有子文件夹。</p>
    </template>
  </li>
</template>
