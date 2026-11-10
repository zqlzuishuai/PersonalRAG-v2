<script setup>
/** archive/FilterRail.vue —— 左栏筛选：只用第三种组件形态（纯文字 + 前置方点） */
import { classes, statuses } from '@/data/registry'
import { useArchiveStore } from '@/stores/archive'
import SectionLabel from '@/components/primitives/SectionLabel.vue'
import DotLink from '@/components/primitives/DotLink.vue'

const archive = useArchiveStore()
</script>

<template>
  <div class="fr">
    <div class="fr__group">
      <SectionLabel en="CLASS" zh="类别" />
      <div class="fr__list">
        <DotLink
          v-for="c in classes"
          :key="c.key"
          :current="archive.cls === c.key"
          @click="archive.setCls(c.key)"
        >
          <span>{{ c.en }}</span>
          <span class="fr__zh">{{ c.zh }}</span>
        </DotLink>
      </div>
    </div>

    <div class="fr__group">
      <SectionLabel en="STATUS" zh="状态" />
      <div class="fr__list">
        <DotLink
          v-for="s in statuses"
          :key="s.key"
          :current="archive.status === s.key"
          @click="archive.setStatus(s.key)"
        >
          <span>{{ s.en }}</span>
          <span class="fr__zh">{{ s.zh }}</span>
        </DotLink>
      </div>
    </div>

    <div class="fr__group">
      <SectionLabel en="COUNT" zh="在册" />
      <div class="fr__count">
        <span class="fr__num mono">{{ String(archive.filtered.length).padStart(2, '0') }}</span>
        <span class="lbl">RECORDS</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fr {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.fr__group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.fr__list {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.fr__zh {
  font-family: var(--font-sans);
  font-size: var(--t95);
  letter-spacing: 1px;
  opacity: 0.8;
}

.fr__count {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.fr__num {
  font-family: var(--font-sans);
  font-size: var(--t46);
  font-weight: 300;
  line-height: 1;
  letter-spacing: -1.5px;
  color: var(--fg);
}
</style>
