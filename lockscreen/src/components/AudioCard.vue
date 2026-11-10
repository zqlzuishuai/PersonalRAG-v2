<script setup>
/**
 * 音频卡片：标题条、封面（半调网点人像剪影）、三枚播放控制、电平条、播放指示点。
 * 关键逻辑：播放状态为组件局部状态；副屏视图由 silent 强制静默且不响应控制；
 * 验证中电平条降频，待机时由全局 is-idle 统一降频。
 */
import { ref, computed } from 'vue'
import { MEDIA, COPY, field } from '../config'
const props = defineProps({
  soundOn: { type: Boolean, default: true },
  silent: { type: Boolean, default: false },
  displayPhase: { type: String, default: 'ready' },
})
const playing = ref(false)
const track = ref(1)
const bars = Array.from({ length: 14 }, (_, i) => i)
const effectivePlaying = computed(() => playing.value && props.soundOn && !props.silent)
const toggle = () => { if (!props.silent && props.soundOn) playing.value = !playing.value }
const shift = (delta) => { if (!props.silent) track.value = Math.max(1, Math.min(9, track.value + delta)) }
const label = computed(() => effectivePlaying.value ? 'RUNNING' : props.silent ? 'MUTED / 静默' : 'STANDBY')
</script>

<template>
  <div class="audio stage-card">
    <div class="audio-head mono micro">
      <span>{{ COPY.audio }}</span><span class="muted">TRK {{ String(track).padStart(2, '0') }}</span>
    </div>
    <div class="audio-body">
      <div class="cover" aria-hidden="true">
        <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">
          <defs>
            <pattern id="halftone" width="4" height="4" patternUnits="userSpaceOnUse">
              <circle cx="1.4" cy="1.4" r="1.1" fill="var(--ink)" opacity="0.85" />
            </pattern>
          </defs>
          <rect width="100" height="100" fill="var(--card)" />
          <path d="M50 22c9 0 14 7 14 16 0 7-4 12-7 15 12 3 21 12 23 26H20c2-14 11-23 23-26-3-3-7-8-7-15 0-9 5-16 14-16z" fill="url(#halftone)" />
          <rect x="0" y="86" width="100" height="14" fill="var(--ink)" opacity="0.9" />
        </svg>
        <span class="cover-tag mono">{{ COPY.classified }}</span>
      </div>

      <div class="audio-info">
        <div class="track-title display ellipsis">{{ field(MEDIA.title) }}</div>
        <div class="track-author mono micro muted ellipsis">{{ field(MEDIA.author) }}</div>
        <div class="controls">
          <button type="button" class="ctrl mono" aria-label="上一轨" :disabled="silent" @click="shift(-1)">◀◀</button>
          <button type="button" class="ctrl ctrl--main mono" :aria-label="effectivePlaying ? '暂停' : '播放'"
                  :disabled="silent || !soundOn" @click="toggle">{{ effectivePlaying ? '❚❚' : '▶' }}</button>
          <button type="button" class="ctrl mono" aria-label="下一轨" :disabled="silent" @click="shift(1)">▶▶</button>
        </div>
      </div>
    </div>

    <div class="level-row">
      <span class="play-dot" :class="{ on: effectivePlaying }" aria-hidden="true"></span>
      <div class="levels" :class="{ paused: !effectivePlaying }" aria-hidden="true">
        <i v-for="b in bars" :key="b" class="level-bar" :style="{ animationDelay: `${b * 63}ms` }"></i>
      </div>
      <span class="mono micro muted">{{ MEDIA.duration }} · {{ label }}</span>
    </div>
  </div>
</template>

<style scoped>
.audio {
  height: 100%;
  padding: 12px 14px;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--ao);
}
.audio-head { display: flex; justify-content: space-between; gap: 8px; padding-bottom: 8px; border-bottom: 1px solid var(--line); }
.audio-body { display: flex; gap: 12px; margin-top: 10px; }
.cover { position: relative; width: 78px; height: 78px; flex: none; border: 1px solid var(--line); overflow: hidden; }
.cover svg { width: 100%; height: 100%; display: block; }
.cover-tag { position: absolute; left: 0; bottom: 0; background: var(--ink); color: var(--paper); font-size: 8px; padding: 2px 4px; letter-spacing: 0.1em; }
.audio-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.track-title { font-size: 17px; line-height: 1.2; }
.track-author { margin-top: 4px; font-size: 10px; }
.controls { display: flex; gap: 8px; margin-top: auto; }
.ctrl {
  width: 34px; height: 26px; border: 1px solid var(--line);
  font-size: 10px; letter-spacing: 0;
  transition: background-color 240ms ease, color 240ms ease, border-color 240ms ease;
}
.ctrl:hover:not(:disabled) { background: var(--ink); color: var(--paper); }
.ctrl--main { width: 46px; border-color: var(--accent); background: var(--accent); color: #111214; }
.ctrl--main:hover:not(:disabled) { background: var(--warn); border-color: var(--warn); }
.level-row { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
.play-dot { width: 7px; height: 7px; flex: none; border-radius: 50%; background: var(--line); }
.play-dot.on { background: var(--accent); box-shadow: 0 0 8px var(--accent); animation: pulse 1s ease-in-out infinite; }
.levels { display: flex; align-items: center; gap: 3px; height: 16px; flex: 1; }
.level-bar { width: 3px; height: 100%; background: var(--ink); transform-origin: center; animation: bar 900ms ease-in-out infinite alternate; }
.levels.paused .level-bar { animation-play-state: paused; transform: scaleY(0.2); opacity: 0.4; }
.level-row .mono { font-size: 9px; flex: none; }
</style>
