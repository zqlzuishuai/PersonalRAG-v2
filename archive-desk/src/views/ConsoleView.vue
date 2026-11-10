<script setup>
/**
 * views/ConsoleView.vue —— 调阅厅
 * 载体配方：桌面仪表盘 —— 左栏筛选与日志流，右侧主面板放档案卡，中栏是登记簿。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useArchiveStore } from '@/stores/archive'
import { useSessionStore } from '@/stores/session'
import { hms } from '@/utils/format'

import SectionLabel from '@/components/primitives/SectionLabel.vue'
import DotLink from '@/components/primitives/DotLink.vue'
import TiltPanel from '@/components/layout/TiltPanel.vue'
import FilterRail from '@/components/archive/FilterRail.vue'
import RegistryTable from '@/components/archive/RegistryTable.vue'
import ClassChart from '@/components/archive/ClassChart.vue'
import LogStream from '@/components/archive/LogStream.vue'
import ArchiveCard from '@/components/archive/ArchiveCard.vue'

const router = useRouter()
const archive = useArchiveStore()
const session = useSessionStore()

const opening = ref(false)
const stamp = ref(hms())
let clock = null
let jump = null

onMounted(() => {
  archive.seed()
  archive.push('CONSOLE MOUNT · READER SLOT 02')
  // 成功入厅后回到常态，避免状态带一直停在 GRANTED
  if (session.phase === 'success') session.phase = 'idle'
  clock = setInterval(() => {
    stamp.value = hms()
  }, 1000)
})

onBeforeUnmount(() => {
  clearInterval(clock)
  clearTimeout(jump)
})

function select(id) {
  archive.select(id)
}

function open(id) {
  if (opening.value) return
  opening.value = true
  archive.push(`RETRIEVE ${id} · IN PROGRESS`)
  jump = setTimeout(() => router.push(`/record/${id}`), 620)
}
</script>

<template>
  <section class="zone zone--a cv__a">
    <SectionLabel en="LEDGER" zh="登记簿" />

    <p class="cv__para">
      全部卷宗按入库年月编排。筛选即时生效，日志流记录每一次动作与来源。
    </p>

    <FilterRail />

    <div class="cv__foot">
      <span class="lbl">SYNC · {{ stamp }}</span>
      <DotLink to="/">BACK TO GATE</DotLink>
    </div>
  </section>

  <section class="zone zone--b cv__b">
    <div class="cv__head">
      <SectionLabel en="REGISTRY" zh="在册" />
      <span class="lbl">INDEX {{ String(archive.filtered.length).padStart(2, '0') }} · {{ stamp }}</span>
    </div>

    <RegistryTable
      :rows="archive.filtered"
      :current="archive.selected?.id"
      @select="select"
    />

    <ClassChart :rows="archive.filtered" :highlight="archive.selected?.cls" />

    <LogStream :lines="archive.logLines" />
  </section>

  <section class="zone zone--c">
    <TiltPanel>
      <ArchiveCard :record="archive.selected" :busy="opening" @open="open" />
    </TiltPanel>
  </section>
</template>

<style scoped>
.cv__a {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-top: 14px;
}

.cv__para {
  font-family: var(--font-sans);
  font-size: var(--t11);
  line-height: 1.7;
  letter-spacing: 0.4px;
  color: var(--dim);
  max-width: 30ch;
}

.cv__foot {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

.cv__b {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  padding-top: 14px;
}

.cv__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex: none;
}

.cv__b :deep(.rt) {
  flex: 1;
  min-height: 0;
}

.cv__b :deep(.ls) {
  flex: none;
}

.mode-column .cv__para {
  max-width: none;
}
</style>
