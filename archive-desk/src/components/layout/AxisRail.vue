<script setup>
/**
 * layout/AxisRail.vue —— 全局唯一的位置型状态指示
 * 画布宽 22% 处一条 2px 竖轴贯穿全高，轴上挂一枚 38×22 强调色标记块，按阶段跳位（4 档）。
 */
import { computed } from 'vue'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const STOPS = [26, 42, 58, 74]

const top = computed(() => `${STOPS[session.stage] || STOPS[0]}%`)
</script>

<template>
  <div class="axis" aria-hidden="true">
    <span v-for="n in 9" :key="n" class="axis__tick" :style="{ top: `${n * 10}%` }" />
    <span class="axis__mark" :style="{ top }" />
  </div>
</template>
