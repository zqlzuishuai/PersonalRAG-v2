<script setup>
import { NSkeleton } from 'naive-ui'
</script>
<template>
  <div class="desk-skeleton" role="status"><span class="sr-only">正在读取资料…</span>
    <table class="desk-load-table" aria-hidden="true"><colgroup><col/><col style="width:190px"/><col style="width:132px"/><col style="width:96px"/></colgroup>
      <thead><tr><th>资料名称</th><th>标签</th><th>更新时间</th><th></th></tr></thead>
      <tbody><tr v-for="(width,index) in ['68%','52%','76%','60%']" :key="index"><td><div class="desk-document"><NSkeleton :animated="false" :width="34" :height="38"/><NSkeleton :animated="false" :width="width" :height="12"/></div></td><td><div class="desk-tags"><NSkeleton :animated="false" :width="48" :height="22"/><NSkeleton :animated="false" :width="38" :height="22"/></div></td><td><NSkeleton :animated="false" :width="76" :height="12"/></td><td><NSkeleton :animated="false" :width="48" :height="12"/></td></tr></tbody>
    </table>
  </div>
</template>
