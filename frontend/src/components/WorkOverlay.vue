<script setup>
import { onMounted, onUnmounted, ref, useId } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router'
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogTitle, DialogDescription } from 'reka-ui'
import AppIcon from './AppIcon.vue'
const props=defineProps({title:String,description:String,kind:{type:String,default:'drawer'},dirty:Boolean,busy:Boolean})
const emit=defineEmits(['close'])
const open=ref(true)
const discard=ref(false)
const descriptionId=useId()
let returnFocus
function requestClose(){if(props.busy||!open.value)return;if(props.dirty){discard.value=true;return}open.value=false}
function discardChanges(){if(!props.busy)open.value=false}
function beforeUnload(event){if(props.dirty||props.busy){event.preventDefault();event.returnValue=''}}
function restoreFocus(event){event.preventDefault();if(returnFocus?.isConnected)returnFocus.focus();if(!open.value)emit('close')}
onMounted(()=>{returnFocus=document.activeElement;window.addEventListener('beforeunload',beforeUnload)})
onUnmounted(()=>window.removeEventListener('beforeunload',beforeUnload))
const canNavigate=to=>to.path==='/login'||(props.busy?false:!props.dirty||window.confirm('有尚未保存的修改，确定离开并放弃修改？'))
onBeforeRouteLeave(canNavigate)
onBeforeRouteUpdate(canNavigate)
defineExpose({requestClose})
</script>
<template>
  <DialogRoot :open="open" @update:open="value=>{if(!value)requestClose()}">
    <DialogPortal>
      <DialogOverlay class="work-backdrop" />
      <DialogContent class="work-overlay" :class="'work-'+kind" :aria-describedby="description?descriptionId:undefined"
        @interact-outside.prevent @escape-key-down="event=>{event.preventDefault();requestClose()}" @close-auto-focus="restoreFocus">
        <header class="overlay-header"><div><DialogTitle>{{title}}</DialogTitle><DialogDescription v-if="description" :id="descriptionId">{{description}}</DialogDescription></div><button class="icon-button" type="button" aria-label="关闭窗口" :disabled="busy" @click="requestClose"><AppIcon name="close"/></button></header>
        <div class="overlay-body"><slot /></div>
        <footer class="overlay-footer">
          <template v-if="discard"><p role="alert">有尚未保存的修改，要放弃吗？</p><button type="button" class="danger" :disabled="busy" @click="discardChanges">放弃修改</button><button type="button" class="primary" :disabled="busy" @click="discard=false">继续编辑</button></template>
          <slot v-else name="footer" :close="requestClose"><button type="button" :disabled="busy" @click="requestClose">关闭</button></slot>
        </footer>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
