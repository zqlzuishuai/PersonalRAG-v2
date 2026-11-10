<script setup>
/**
 * 演示控制层（非设计范式模块，仅用于逐项验收，可整块关闭）。
 * 关键逻辑：集中暴露状态跳转、三种验证结果注入、能力开关与画质分档，
 * 便于对照验收「就绪 / 验证中 / 拒绝」「全局反相」「副屏」「降级」等条目。
 */
import { ref, nextTick } from 'vue'
import { PHASE_SEQUENCE } from '../config'
const props = defineProps({
  machine: { type: Object, required: true },
  capabilities: { type: Object, required: true },
  hasDesktopFrame: { type: Boolean, default: true },
})
const emit = defineEmits(['update:hasDesktopFrame'])
const open = ref(false)
const switches = [
  { key: 'threeD', label: '3D / 三维背景' },
  { key: 'mediaCard', label: 'MEDIA / 媒体卡片' },
  { key: 'powerItems', label: 'POWER / 电源项' },
  { key: 'sound', label: 'SOUND / 声音开关' },
  { key: 'secondaryView', label: 'SECOND / 副屏视图' },
  { key: 'fallbackView', label: 'FALLBACK / 降级视图' },
]
const qualities = ['high', 'medium', 'low']
const outcomes = [
  { id: 'grant', label: 'GRANT / 通过' },
  { id: 'policy', label: 'POLICY / 策略拒绝' },
  { id: 'deny', label: 'DENY / 凭据被拒' },
]

const toggleSwitch = (key) => {
  props.capabilities[key] = !props.capabilities[key]
  if (key === 'secondaryView' && props.capabilities[key]) props.capabilities.fallbackView = false
  if (key === 'fallbackView' && props.capabilities[key]) props.capabilities.secondaryView = false
  props.machine.pushLog(`CAP · ${key.toUpperCase()} ${props.capabilities[key] ? 'ON' : 'OFF'}`)
}
const runDemo = async (kind) => {
  if (props.machine.phase !== 'ready') {
    props.machine.goToPhase('ready')
    await nextTick()
  }
  props.machine.demo(kind)
}
</script>

<template>
  <div class="demo" :class="{ open }">
    <button type="button" class="demo-toggle mono micro" :aria-expanded="open" @click="open = !open">
      {{ open ? 'DEMO CONSOLE ×' : 'DEMO / 演示控制' }}
    </button>

    <div v-if="open" class="demo-body">
      <p class="demo-note mono micro">
        演示控制层 · 非设计范式模块<br />可整块关闭，不参与画面验收。
      </p>

      <div class="group">
        <div class="group-title mono micro">STATE / 状态跳转</div>
        <div class="chips">
          <button v-for="p in PHASE_SEQUENCE" :key="p" type="button" class="chip mono"
                  :class="{ on: machine.displayPhase === p }" @click="machine.goToPhase(p)">{{ p }}</button>
        </div>
      </div>

      <div class="group">
        <div class="group-title mono micro">VERIFY / 结果注入</div>
        <div class="chips">
          <button v-for="o in outcomes" :key="o.id" type="button" class="chip mono" @click="runDemo(o.id)">{{ o.label }}</button>
        </div>
        <div class="chips">
          <button type="button" class="chip mono" @click="machine.enterIdle()">IDLE / 待机</button>
          <button type="button" class="chip mono" @click="machine.wake()">WAKE / 唤醒</button>
          <button type="button" class="chip mono" @click="machine.relock()">RELOCK / 重新锁定</button>
        </div>
      </div>

      <div class="group">
        <div class="group-title mono micro">CAPABILITY / 能力开关</div>
        <div class="switches">
          <button v-for="s in switches" :key="s.key" type="button" class="switch mono micro"
                  :aria-pressed="capabilities[s.key]" @click="toggleSwitch(s.key)">
            <i :class="{ on: capabilities[s.key] }"></i>{{ s.label }}
          </button>
        </div>
        <label class="switch mono micro frame-switch">
          <input type="checkbox" :checked="hasDesktopFrame"
                 @change="emit('update:hasDesktopFrame', $event.target.checked)" />
          FRAME / 桌面画面
        </label>
      </div>

      <div class="group">
        <div class="group-title mono micro">QUALITY / 画质分档</div>
        <div class="chips">
          <button v-for="q in qualities" :key="q" type="button" class="chip mono"
                  :class="{ on: capabilities.quality === q }"
                  @click="capabilities.quality = q; machine.pushLog('QUALITY · ' + q.toUpperCase())">{{ q }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.demo { position: fixed; right: 14px; bottom: 14px; z-index: 40; font-size: 11px; }
.demo-toggle { padding: 8px 12px; background: var(--ink); color: var(--paper); font-size: 10px; letter-spacing: 0.14em; border: 1px solid var(--accent); }
.demo-toggle:hover { background: var(--accent); color: #111214; }
.demo-body {
  width: min(360px, calc(100vw - 28px));
  max-height: min(62vh, 520px); overflow-y: auto;
  margin-bottom: 8px; padding: 14px;
  background: var(--card); border: 1px solid var(--line); box-shadow: var(--shadow);
}
.demo-note { margin: 0 0 12px; color: var(--muted); line-height: 1.7; font-size: 9px; }
.group { border-top: 1px solid var(--line); padding-top: 10px; margin-top: 10px; }
.group-title { color: var(--muted); margin-bottom: 8px; font-size: 9px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
.chip { padding: 5px 8px; border: 1px solid var(--line); font-size: 9px; letter-spacing: 0.06em; }
.chip:hover { border-color: var(--ink); }
.chip.on { background: var(--accent); border-color: var(--accent); color: #111214; }
.switches { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.switch { display: flex; align-items: center; gap: 7px; padding: 5px 6px; border: 1px solid var(--line-soft); font-size: 9px; text-align: left; }
.switch i { width: 8px; height: 8px; flex: none; background: transparent; border: 1px solid var(--ink); }
.switch i.on { background: var(--accent); border-color: var(--accent); }
.frame-switch { margin-top: 8px; width: 100%; cursor: pointer; }
.frame-switch input { accent-color: var(--accent); }
</style>
