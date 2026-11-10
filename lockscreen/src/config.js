/**
 * ============================================================
 * 提示词「变量」区 —— 只替换取值，不改变状态数量、层级关系与规则。
 * 所有文案、字段、能力开关集中在此，组件不硬编码取值。
 * 约束：界面与配置中均不出现任何凭据明文。
 * ============================================================
 */

// 色板：浅底深字 + 单一荧光强调 + 单一警示色。反相由 styles.css 的
// [data-tone="reject"] 整幅覆盖，不是局部弹窗。
export const PALETTE = {
  paper: '#e7e5e1',
  ink: '#111214',
  accent: '#b9e432',
  warn: '#ff7b00',
  warnDeep: '#e35d00',
  card: '#f6f5f2',
}

// 三行锁死式字标：首行最大；次行以字距对齐首行宽度；末行两词粗细对比。
export const WORDMARK = {
  first: 'SESSION',
  second: 'ARCHIVE',
  thirdStrong: 'LOCK',
  thirdThin: 'TERMINAL',
}

// 内容字段（示意数据）。省略时由 field() 呈现中性占位符，不留空白区。
export const PLACEHOLDER = '—'
export const field = (value) =>
  value === undefined || value === null || value === '' ? PLACEHOLDER : value

export const IDENTITY = {
  operator: 'CHEN M. / 陈默',
  host: 'WS-07 · LAB-NORTH',
  session: 'S-4417 / TTY2',
  keyboard: 'US · 104 / QWERTY',
  clearance: 'LEVEL 03 · SUPERVISED',
  fileCode: 'FR-0441 / SEALED',
}

export const MEDIA = {
  title: 'FIELD RECORDING NO. 4',
  author: 'ARCHIVE / UNATTRIBUTED',
  duration: '04:12',
}

// 电源项：所有电源类操作都需二次确认（见 FooterBar.vue）。
export const POWER_ITEMS = [
  { id: 'resume', label: 'RESUME', zh: '返回会话' },
  { id: 'sleep', label: 'SUSPEND', zh: '挂起' },
  { id: 'poweroff', label: 'POWER OFF', zh: '关机' },
]

export const SHORTCUTS = [
  { key: 'ENTER', label: 'SUBMIT' },
  { key: 'ESC', label: 'CLEAR' },
  { key: 'ALT+←→', label: 'CYCLE FOCUS' },
  { key: 'ANY', label: 'WAKE' },
]

export const SECTIONS = [
  { no: '01', label: 'SEAL / 封存' },
  { no: '02', label: 'VERIFY / 比对' },
  { no: '03', label: 'RELEASE / 解封' },
]

// 步骤点：随状态前移，数量固定。
export const STEPS = ['SEAL', 'IDLE', 'VERIFY', 'RELEASE']

// 状态顺序固定，不随变量改变。typing 是 ready 的派生显示态。
export const PHASE_SEQUENCE = [
  'entering', 'ready', 'typing', 'verifying',
  'rejected', 'approved', 'exiting', 'idle',
]

// 档案／命令／仪器语汇：全大写短标签，中点与编号组织，无寒暄。
export const COPY = {
  archive: 'ARCHIVE · 档案',
  specimen: 'SPECIMEN · 标本',
  audio: 'AUDIO STRIP · 声轨',
  authorize: 'AUTHORIZE · 授权',
  submit: 'VERIFY / 提交',
  verifying: 'COMPARING / 比对中',
  clear: 'CLEAR',
  classified: 'CLASSIFIED',
  confidential: 'CONFIDENTIAL / 保密',
  sound: 'SOUND',
  idleHint: 'PRESS ANY KEY · 按任意键唤醒',
  welcomeName: 'CHEN M.',
  leaderA: 'FIG. 01 — SEALED FRAME',
  leaderB: 'FIG. 02 — IDENTITY BLOCK',
  signature: 'ARCHIVE UNIT / LAB-NORTH · 04',
}

// 双语字幕：中文完整句，英文同义对应，随状态同步切换。
export const SUBTITLES = {
  entering: { zh: '正在封存当前会话画面并归档。', en: 'SEALING THE CURRENT SESSION FRAME FOR ARCHIVE.' },
  ready: { zh: '会话已封存，请输入授权凭据。', en: 'SESSION SEALED. AWAITING CREDENTIAL INPUT.' },
  typing: { zh: '正在记录凭据长度，不显示明文。', en: 'RECORDING CREDENTIAL LENGTH. PLAINTEXT SUPPRESSED.' },
  verifying: { zh: '正在与档案凭据进行比对。', en: 'COMPARING CREDENTIAL AGAINST THE ARCHIVE.' },
  rejected: { zh: '凭据未通过校验，会话保持锁定。', en: 'CREDENTIAL REJECTED. SESSION REMAINS LOCKED.' },
  approved: { zh: '凭据通过，正在解封会话画面。', en: 'CREDENTIAL ACCEPTED. RELEASING THE SEALED FRAME.' },
  exiting: { zh: '会话画面正在恢复至锁定前状态。', en: 'RESTORING THE FRAME TO ITS PRE-LOCK STATE.' },
  idle: { zh: '终端已进入待机，按任意键唤醒。', en: 'TERMINAL IDLE. PRESS ANY KEY TO WAKE.' },
}

// 错误文案只陈述事实，并区分两种拒绝原因。
export const REJECTION = {
  credential: {
    title: 'CREDENTIAL REJECTED',
    zh: '凭据被拒：与档案记录不匹配。',
    en: 'CREDENTIAL DOES NOT MATCH THE ARCHIVE RECORD.',
  },
  policy: {
    title: 'SESSION POLICY REJECTED',
    zh: '凭据已通过，但会话被策略拒绝。',
    en: 'CREDENTIAL ACCEPTED; SESSION REJECTED BY POLICY.',
  },
}

// 警示板四条逐行出现的记录；attempts 与状态机同步。
export const warningRecords = (reason, attempts, lockedAt) => [
  `01 · EVENT / ${reason === 'policy' ? 'POLICY GATE' : 'AUTH MISMATCH'}`,
  `02 · SOURCE / ${IDENTITY.host}`,
  `03 · TIME / ${lockedAt} · ATTEMPT ${String(attempts).padStart(2, '0')}`,
  `04 · ACTION / SESSION REMAINS SEALED`,
]

// 能力开关：默认全开。关闭某项只移除对应组件，其余元素不重排、不补位。
// secondaryView / fallbackView 是「可切换的视图能力」，其启用状态由控制台或 URL 决定。
export const DEFAULT_CAPABILITIES = {
  threeD: true,
  mediaCard: true,
  powerItems: true,
  sound: true,
  secondaryView: false,
  fallbackView: false,
  secondaryAvailable: true,
  fallbackAvailable: true,
  quality: 'high', // high → medium → low：逐级去掉阴影、环境遮蔽与景深
}

export const MAX_SECRET_LENGTH = 32

// 输入格按可用宽度自适应折叠；此为单格基准宽度（px，1920 基准画布）。
export const SLOT_WIDTH = 20
export const SLOT_GAP = 4
