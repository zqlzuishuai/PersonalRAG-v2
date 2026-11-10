<script setup>
/**
 * 三行锁死式字标。
 * 关键逻辑：首行最大；次行用 flex space-between 把字符字距拉到与首行同宽；
 * 末行两个词使用 900 / 200 字重对比。文案全部来自 config 变量。
 */
import { WORDMARK, COPY } from '../config'
const secondChars = [...WORDMARK.second]
</script>

<template>
  <div class="wordmark" :aria-label="`${WORDMARK.first} ${WORDMARK.second}`">
    <!-- lockup 收缩到首行文字宽度，次行 space-between 才能精确对齐首行 -->
    <div class="lockup">
      <div class="first display">{{ WORDMARK.first }}</div>
      <div class="second thin" aria-hidden="true">
        <span v-for="(ch, i) in secondChars" :key="i">{{ ch }}</span>
      </div>
    </div>
    <div class="third">
      <strong class="display">{{ WORDMARK.thirdStrong }}</strong>
      <span class="thin">{{ WORDMARK.thirdThin }}</span>
    </div>
    <div class="wm-meta mono micro muted">
      <span class="cursor-square"></span>
      {{ COPY.archive }} · NO. 04 / SEALED UNIT
    </div>
  </div>
</template>

<style scoped>
.wordmark { line-height: 0.9; user-select: none; }
.lockup { display: inline-block; }
.first { font-size: 78px; letter-spacing: -0.045em; white-space: nowrap; }
.second {
  display: flex;
  justify-content: space-between;
  width: 100%;
  margin-top: 6px;
  font-family: var(--font-display);
  font-size: 30px;
  letter-spacing: 0;
  border-bottom: 1px solid var(--line);
  padding-bottom: 8px;
}
.third { display: flex; align-items: baseline; gap: 14px; margin-top: 10px; }
.third strong { font-size: 26px; }
.third .thin { font-family: var(--font-display); font-size: 26px; letter-spacing: 0.04em; }
.wm-meta { display: flex; align-items: center; gap: 10px; margin-top: 18px; }
@media (max-width: 520px) {
  .first { font-size: 48px; }
  .second { font-size: 18px; }
  .third strong, .third .thin { font-size: 18px; }
}
</style>
