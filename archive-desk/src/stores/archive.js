import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { records, streamLines } from '@/data/registry'
import { hms } from '@/utils/format'

/**
 * stores/archive.js
 * 登记簿的筛选、选中与日志流。日志流是「信息必须有出处」的落地形态之一。
 */
export const useArchiveStore = defineStore('archive', () => {
  const cls = ref('ALL')
  const status = ref('ALL')
  const selectedId = ref('A-0317')
  const logLines = ref([])

  const filtered = computed(() =>
    records.filter(
      (r) => (cls.value === 'ALL' || r.cls === cls.value) && (status.value === 'ALL' || r.status === status.value),
    ),
  )

  const selected = computed(
    () => filtered.value.find((r) => r.id === selectedId.value) || filtered.value[0] || records[0],
  )

  function stamp() {
    return hms()
  }

  function push(text) {
    logLines.value.push({ id: `${Date.now()}-${Math.random().toString(16).slice(2, 6)}`, t: stamp(), text })
    if (logLines.value.length > 6) logLines.value.shift()
  }

  function select(id) {
    selectedId.value = id
    push(`FOCUS ${id} · PANEL SYNC`)
  }

  function setCls(v) {
    cls.value = v
    push(`FILTER CLASS = ${v}`)
  }

  function setStatus(v) {
    status.value = v
    push(`FILTER STATUS = ${v}`)
  }

  function seed() {
    if (logLines.value.length) return
    push('SESSION OPEN · READER SLOT 02')
    push('LEDGER INDEX LOADED · 9 RECORDS')
    push(streamLines[2])
    push('SEAL INTEGRITY CHECK · PASS')
  }

  return { cls, status, selectedId, logLines, filtered, selected, push, select, setCls, setStatus, seed, stamp }
})
