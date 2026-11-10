<script setup>
/** archive/RegistryTable.vue —— 登记簿：无斑马纹、无竖线，仅表头下一条 1.5px 横线 */
import Tag from '@/components/primitives/Tag.vue'

defineProps({
  rows: { type: Array, required: true },
  current: { type: String, default: '' },
})

defineEmits(['select'])
</script>

<template>
  <div class="rt">
    <table class="rtable">
      <thead>
        <tr>
          <th style="width: 88px">REF</th>
          <th>TITLE</th>
          <th style="width: 96px">CLASS</th>
          <th style="width: 78px">SHELF</th>
          <th style="width: 118px">STATUS</th>
          <th style="width: 84px">ACC.</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="r in rows"
          :key="r.id"
          :class="{ 'is-current': r.id === current }"
          tabindex="0"
          @click="$emit('select', r.id)"
          @keydown.enter.prevent="$emit('select', r.id)"
          @keydown.space.prevent="$emit('select', r.id)"
        >
          <td class="mono">{{ r.id }}</td>
          <td class="cell-title">{{ r.zh }}</td>
          <td>{{ r.clsEn }}</td>
          <td class="mono">{{ r.shelf }}</td>
          <td>
            <Tag :variant="r.status === 'OPEN' ? 'outline' : 'solid'">{{ r.status }}</Tag>
          </td>
          <td class="mono">{{ r.year }}</td>
        </tr>
        <tr v-if="!rows.length">
          <td colspan="6" class="rt__empty">NO RECORD MATCHES THE FILTER</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.rt {
  min-height: 0;
  overflow: auto;
}

.rt__empty {
  padding: 22px 10px;
  color: var(--dim);
  letter-spacing: 1.2px;
}
</style>
