<script setup>
/**
 * views/RecordView.vue —— 单卷档案
 * 载体配方：后台详情页 —— 表格规则、编号与时间戳、实心表头；
 * 主操作仍是全屏唯一：申请复本。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { recordById, records } from '@/data/registry'
import { useArchiveStore } from '@/stores/archive'

import SectionLabel from '@/components/primitives/SectionLabel.vue'
import Tag from '@/components/primitives/Tag.vue'
import DotLink from '@/components/primitives/DotLink.vue'
import FieldTable from '@/components/primitives/FieldTable.vue'
import TiltPanel from '@/components/layout/TiltPanel.vue'
import ArchiveCard from '@/components/archive/ArchiveCard.vue'

const props = defineProps({ id: { type: String, default: '' } })

const router = useRouter()
const archive = useArchiveStore()
const record = computed(() => recordById(props.id))

const requesting = ref(false)
let jump = null

onMounted(() => {
  if (!record.value) {
    router.replace('/console')
    return
  }
  archive.selectedId = record.value.id
  archive.push(`OPEN ${record.value.id} · DETAIL VIEW`)
})

watch(
  () => props.id,
  (id) => {
    if (!recordById(id)) {
      router.replace('/console')
      return
    }
    archive.selectedId = id
    archive.push(`OPEN ${id} · DETAIL VIEW`)
  },
)

onBeforeUnmount(() => clearTimeout(jump))

const mini = computed(() => {
  const r = record.value
  if (!r) return []
  return [
    { k: 'SHELF', v: r.shelf },
    { k: 'ACCESSION', v: r.year },
    { k: 'UNIT', v: r.unit },
  ]
})

const handling = computed(() => {
  const r = record.value
  if (!r) return []
  return r.log.map((line) => {
    const i = line.indexOf(' ')
    return { t: line.slice(0, i), x: line.slice(i + 1) }
  })
})

const related = computed(() => {
  const r = record.value
  if (!r) return []
  const pool = records.filter((x) => x.id !== r.id)
  const same = pool.filter((x) => x.cls === r.cls)
  const rest = pool.filter((x) => x.cls !== r.cls)
  return [...same, ...rest].slice(0, 3).map((x) => ({
    id: x.id,
    zh: x.zh,
    rel: x.cls === r.cls ? 'SAME CLASS' : 'SAME SHELF ZONE',
  }))
})

function go(id) {
  router.push(`/record/${id}`)
}

function request() {
  if (requesting.value || !record.value) return
  requesting.value = true
  archive.push(`REPLICA REQUEST ${record.value.id} · QUEUED`)
  jump = setTimeout(() => {
    requesting.value = false
  }, 1600)
}
</script>

<template>
  <template v-if="record">
    <section class="zone zone--a rv__a">
      <SectionLabel en="RECORD" zh="卷宗" />

      <h1 class="rv__id mono">{{ record.id }}</h1>

      <div class="rv__tags">
        <Tag>{{ record.clsEn }}</Tag>
        <Tag variant="outline">{{ record.status }}</Tag>
      </div>

      <FieldTable class="rv__ft" :items="mini" />

      <div class="rv__foot">
        <DotLink to="/console">BACK TO REGISTRY</DotLink>
      </div>
    </section>

    <section class="zone zone--b rv__b">
      <div class="rv__head">
        <SectionLabel en="ABSTRACT" zh="摘要" />
        <span class="lbl">REF {{ record.id }} · {{ record.year }}</span>
      </div>

      <p class="rv__abstract">{{ record.abstract }}</p>

      <div class="rv__block">
        <SectionLabel en="HANDLING" zh="处理记录" />
        <table class="rtable rv__table rv__table--static">
          <thead>
            <tr>
              <th style="width: 108px">STAMP</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in handling" :key="h.t + h.x">
              <td class="mono">{{ h.t }}</td>
              <td class="cell-title">{{ h.x }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="rv__block">
        <SectionLabel en="RELATED" zh="关联" />
        <table class="rtable rv__table">
          <thead>
            <tr>
              <th style="width: 108px">REF</th>
              <th>TITLE</th>
              <th style="width: 168px">RELATION</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="r in related"
              :key="r.id"
              tabindex="0"
              @click="go(r.id)"
              @keydown.enter.prevent="go(r.id)"
            >
              <td class="mono">{{ r.id }}</td>
              <td class="cell-title">{{ r.zh }}</td>
              <td class="mono">{{ r.rel }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="rv__block rv__block--row">
        <div class="rv__cell">
          <SectionLabel en="SOURCE" zh="来源" />
          <p class="rv__kv mono">{{ record.fields[1]?.v || '—' }}</p>
        </div>
        <div class="rv__cell">
          <SectionLabel en="UNIT" zh="计量" />
          <p class="rv__kv mono">{{ record.unit }}</p>
        </div>
      </div>
    </section>

    <section class="zone zone--c">
      <TiltPanel>
        <ArchiveCard
          :record="record"
          :busy="requesting"
          action-en="REQUEST COPY"
          action-zh="申请复本"
          busy-en="QUEUING"
          busy-zh="排队中"
          @open="request"
        />
      </TiltPanel>
    </section>
  </template>
</template>

<style scoped>
.rv__a {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-top: 14px;
}

.rv__id {
  font-family: var(--font-sans);
  font-size: var(--t46);
  font-weight: 300;
  line-height: 1;
  letter-spacing: -1.5px;
  color: var(--fg);
}

.rv__tags {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rv__ft {
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

.rv__foot {
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

.rv__b {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 0;
  padding-top: 14px;
  overflow: auto;
}

.rv__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.rv__abstract {
  font-family: var(--font-sans);
  font-size: var(--t15);
  line-height: 1.75;
  letter-spacing: 0.4px;
  color: var(--fg);
  max-width: 46ch;
}

.rv__block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rv__block--row {
  flex-direction: row;
  gap: 40px;
}

.rv__cell {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rv__kv {
  font-size: var(--t125);
  color: var(--fg);
}

.rv__table tbody tr {
  cursor: pointer;
}

.rv__table--static tbody tr {
  cursor: default;
}

.rv__table td.cell-title {
  font-family: var(--font-sans);
  font-size: var(--t125);
}

.mode-column .rv__abstract {
  max-width: none;
}
</style>
