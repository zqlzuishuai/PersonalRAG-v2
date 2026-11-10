<script setup>
/** layout/StatusBand.vue —— 状态带：阶段指示、次级操作、署名 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import Tag from '@/components/primitives/Tag.vue'
import DotLink from '@/components/primitives/DotLink.vue'
import { useSessionStore } from '@/stores/session'
import { useCurtainStore } from '@/stores/curtain'
import { org } from '@/data/registry'

const session = useSessionStore()
const curtain = useCurtainStore()
const router = useRouter()

const stateWord = computed(
  () =>
    ({
      idle: 'STANDBY',
      working: 'AUTHORIZING',
      failure: 'DENIED',
      success: 'GRANTED',
    })[session.phase] || 'STANDBY',
)

const stateVariant = computed(() => {
  if (session.phase === 'failure') return 'alert'
  if (session.phase === 'working') return 'accent'
  return 'solid'
})

function leave() {
  session.hardReset()
  router.push('/')
}
</script>

<template>
  <div class="sb">
    <div class="sb__left">
      <Tag :variant="stateVariant">{{ stateWord }}</Tag>
      <span class="sb__stage">
        STAGE {{ String(session.stage + 1).padStart(2, '0') }} · {{ session.stageLabel }}
      </span>
      <span class="sb__zh">{{ session.stageZh }}</span>
    </div>

    <div class="sb__mid">
      <DotLink @click="curtain.toggle()">{{ curtain.isInk ? 'PAPER' : 'INK' }} CURTAIN</DotLink>
      <DotLink to="/console" :current="$route.name === 'console'">CONSOLE</DotLink>
      <DotLink to="/spec" :current="$route.name === 'spec'">SPEC</DotLink>
      <DotLink @click="leave">SIGN OUT</DotLink>
    </div>

    <div class="sb__right">
      <span class="sb__power">POWERED BY {{ org.zh }}</span>
      <i class="dash" />
    </div>
  </div>
</template>

<style scoped>
.sb {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gutter);
  width: 100%;
}

.sb__left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  white-space: nowrap;
}

.sb__stage {
  font-family: var(--font-mono);
  font-size: var(--t11);
  font-weight: 600;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: var(--fg);
}

.sb__zh {
  font-family: var(--font-sans);
  font-size: var(--t95);
  letter-spacing: 1px;
  color: var(--dim);
}

.sb__mid {
  display: flex;
  align-items: center;
  gap: 22px;
  min-width: 0;
}

.sb__right {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
}

.sb__power {
  font-family: var(--font-mono);
  font-size: var(--t8);
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: var(--dim);
}
</style>
