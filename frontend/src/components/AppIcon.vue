<script setup>
import {BookOpen,Library,Search,Trash2,FileText,Folder,Upload,UserRound,LogOut,Sparkles,X,Plus,ArrowUpRight,ChevronRight,ArrowLeft,RefreshCw,SlidersHorizontal,PanelLeft,FolderInput} from 'lucide-vue-next'
defineProps({name:{type:String,default:'file'},size:{type:Number,default:20}})
const icons={brand:BookOpen,library:Library,search:Search,trash:Trash2,file:FileText,folder:Folder,upload:Upload,user:UserRound,logout:LogOut,spark:Sparkles,close:X,plus:Plus,external:ArrowUpRight,chevron:ChevronRight,back:ArrowLeft,refresh:RefreshCw,filter:SlidersHorizontal,panel:PanelLeft,move:FolderInput}
</script>
<template><component :is="icons[name]||FileText" class="app-icon" :size="size" :stroke-width="1.7" aria-hidden="true"/></template>
