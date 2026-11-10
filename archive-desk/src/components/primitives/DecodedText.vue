<script setup>
/**
 * primitives/DecodedText.vue
 * 逐字解码：字符先为灰色乱码，尾部保留 3 个乱码位，约 32ms/字。
 * 同一段文字在本次会话内只解码一次（登记在 stores/decode）。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useDecodeStore } from '@/stores/decode'

const props = defineProps({
  text: { type: String, default: '' },
  speed: { type: Number, default: 32 },
  tag: { type: String, default: 'span' },
  keyName: { type: String, default: '' },
})

const GLYPH = '▓▒░▚▞▛▟#%&@$/*+<>=^'
const rnd = () => GLYPH[(Math.random() * GLYPH.length) | 0]

const decode = useDecodeStore()
const chars = computed(() => Array.from(props.text || ''))
const noise = ref([])
const revealed = ref(0)

let timer = null

function settle() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  revealed.value = chars.value.length
}

function run() {
  if (timer) clearInterval(timer)
  timer = null
  const list = chars.value
  if (!list.length) return

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduce || !decode.claim(props.keyName || props.text)) {
    settle()
    return
  }

  noise.value = list.map(() => rnd())
  revealed.value = 0

  timer = setInterval(() => {
    revealed.value += 1
    const from = revealed.value
    const to = Math.min(list.length, from + 3)
    for (let i = from; i < to; i += 1) noise.value[i] = rnd()
    if (revealed.value >= list.length) settle()
  }, props.speed)
}

onMounted(run)
watch(() => props.text, run)
onBeforeUnmount(() => timer && clearInterval(timer))
</script>

<template>
  <component :is="tag" class="dt">
    <span
      v-for="(c, i) in chars"
      :key="i"
      class="dt__c"
      :class="{ 'is-on': i < revealed }"
    >{{ i < revealed ? (c === ' ' ? '\u00a0' : c) : (noise[i] || '░') }}</span>
  </component>
</template>

<style scoped>
.dt {
  white-space: nowrap;
}

.dt__c {
  color: var(--dim);
  opacity: 0.55;
}

.dt__c.is-on {
  color: inherit;
  opacity: 1;
}
</style>
