<script setup>
/** 引线标注与署名横条：纯装饰性档案标注，不承载交互，紧凑布局下隐藏。 */
import { COPY } from '../config'
</script>

<template>
  <div class="leaders" aria-hidden="true">
    <svg class="leader-svg" viewBox="0 0 840 70" preserveAspectRatio="none">
      <path d="M0 34 H260 L292 8 H600" fill="none" stroke="var(--line)" stroke-width="1" />
      <path d="M0 54 H180 L214 62 H520" fill="none" stroke="var(--line)" stroke-width="1" />
      <circle cx="260" cy="34" r="3" fill="var(--accent)" />
      <circle cx="180" cy="54" r="3" fill="var(--ink)" />
      <rect x="596" y="4" width="8" height="8" fill="none" stroke="var(--ink)" />
    </svg>
    <span class="leader-label mono micro muted">{{ COPY.leaderA }}</span>
    <span class="leader-label b mono micro muted">{{ COPY.leaderB }}</span>
  </div>
</template>

<style scoped>
.leaders { position: relative; opacity: 0.85; }
.leader-svg { width: 100%; height: 70px; display: block; }
.leader-label { position: absolute; left: 0; top: -2px; }
.leader-label.b { left: 300px; top: 42px; }
</style>
