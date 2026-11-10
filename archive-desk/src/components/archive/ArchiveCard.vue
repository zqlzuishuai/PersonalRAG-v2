<script setup>
/** archive/ArchiveCard.vue —— 主面板里的「档案卡」：标签块 → 字段表 → 编号 → 时间戳 → 单位 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import Tag from '@/components/primitives/Tag.vue'
import FieldTable from '@/components/primitives/FieldTable.vue'
import PrimaryAction from '@/components/primitives/PrimaryAction.vue'
import SectionLabel from '@/components/primitives/SectionLabel.vue'
import DecodedText from '@/components/primitives/DecodedText.vue'
import { hms } from '@/utils/format'

const props = defineProps({
  record: { type: Object, required: true },
  busy: { type: Boolean, default: false },
  actionEn: { type: String, default: 'OPEN RECORD' },
  actionZh: { type: String, default: '调阅此卷' },
  busyEn: { type: String, default: 'RETRIEVING' },
  busyZh: { type: String, default: '调取中' },
})

defineEmits(['open'])

const stamp = ref(hms())
const tick = setInterval(() => {
  stamp.value = hms()
}, 1000)
onBeforeUnmount(() => clearInterval(tick))

watch(
  () => props.record.id,
  () => {
    stamp.value = hms()
  },
)

const statusVariant = computed(() => (props.record.status === 'OPEN' ? 'outline' : 'solid'))
</script>

<template>
  <div class="ac">
    <span class="ac__ghost" aria-hidden="true">{{ record.id.split('-')[1] }}</span>

    <div class="ac__head">
      <SectionLabel en="SECTION PROFILE" />
      <Tag :variant="statusVariant">{{ record.status }}</Tag>
    </div>

    <div class="ac__body">
      <div class="ac__tags">
        <Tag>{{ record.clsEn }}</Tag>
        <span class="lbl">{{ record.cls }}</span>
      </div>

      <h2 class="ac__zh">{{ record.zh }}</h2>
      <DecodedText class="ac__en lbl" :text="record.en" />

      <FieldTable class="ac__ft" :items="record.fields" />

      <p class="ac__excerpt">{{ record.abstract }}</p>

      <div class="ac__meta">
        <span class="ac__ref mono">{{ record.id }}</span>
        <span class="ac__dot" />
        <span class="mono">{{ record.unit }}</span>
      </div>
      <div class="ac__stamp">
        <span class="lbl">ACCESSED {{ stamp }}</span>
        <span class="lbl">SHELF {{ record.shelf }}</span>
      </div>
    </div>

    <div class="ac__foot">
      <PrimaryAction
        :en="actionEn"
        :zh="actionZh"
        :busy-en="busyEn"
        :busy-zh="busyZh"
        :busy="busy"
        @click="$emit('open', record.id)"
      />
    </div>
  </div>
</template>

<style scoped>
.ac {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.ac__ghost {
  position: absolute;
  right: -12px;
  bottom: 52px;
  font-family: var(--font-sans);
  font-size: var(--t112);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -4px;
  color: var(--fg);
  opacity: 0.06;
  pointer-events: none;
  user-select: none;
}

.ac__head {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 14px;
  border-bottom: 1px solid var(--line);
  flex: none;
}

.ac__body {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  padding: 16px 14px 8px;
  display: flex;
  flex-direction: column;
}

.ac__tags {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ac__zh {
  margin-top: 12px;
  font-family: var(--font-sans);
  font-size: var(--t21);
  font-weight: 600;
  line-height: 1.1;
  letter-spacing: -0.2px;
  color: var(--fg);
}

.ac__en {
  margin-top: 6px;
  color: var(--dim);
}

.ac__ft {
  margin-top: 18px;
}

.ac__excerpt {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
  font-family: var(--font-sans);
  font-size: var(--t11);
  line-height: 1.75;
  letter-spacing: 0.3px;
  color: var(--dim);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ac__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1.5px solid var(--hair);
  font-size: var(--t95);
  color: var(--dim);
  white-space: nowrap;
  overflow: hidden;
}

.ac__ref {
  color: var(--fg);
  letter-spacing: 1.2px;
}

.ac__dot {
  width: 3px;
  height: 3px;
  background: var(--dim);
  flex: none;
}

.ac__stamp {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
}

.ac__foot {
  position: relative;
  z-index: 1;
  flex: none;
  padding: 0 14px 14px;
}
</style>
