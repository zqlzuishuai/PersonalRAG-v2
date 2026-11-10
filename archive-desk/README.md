# 恒序档案署 · PERPETUAL ARCHIVE

把《可移植界面风格提示词》的 **B 段风格约束层**落成一个能跑、能改、能验收的 Vue 3 应用。
内容层（一个虚构的档案署）只决定「说什么」，风格层决定「长什么样」。

技术栈：Vue 3（`<script setup>`）+ Vite 6 + Vue Router 4 + Pinia 2，没有任何 UI 库、图标库、CSS 框架——形态白名单里本来也不允许。

---

## 一、先拆需求：提示词的每一条落到哪里

| 提示词条目 | 实现落点 |
| --- | --- |
| 两个完整色幕 + 0→1 幕值整体插值 | `styles/tokens.css`（`--curtain` + `color-mix`）、`stores/curtain.js` |
| 只允许两个彩色、面积 ≤5% | `tokens.css` 的 `--accent` / `--alert`；全站仅用于光标、进度、状态环、当前项、错误 |
| 字号阶梯 10 级 | `tokens.css` 的 `--t8 … --t92`（另 `--t112` 只给幽灵字） |
| 两族字体分工 | `public/fonts/` 自托管 Montserrat（几何无衬线）+ JetBrains Mono（等宽） |
| 12 列网格 / 三条横带 / 22% 竖轴 | `styles/base.css`：`.canvas` `.band--brand` `.band--main` `.band--status` `.axis` |
| 轴上 38×22 强调块按阶段跳位（≤4 档） | `components/layout/AxisRail.vue` + `stores/session.js` 的 `stage` |
| 5:7 分栏、主面板 33–36% 贴右边距 | `.band--main { grid-template-columns: 22% 40% auto }` + `.zone--c` |
| 主面板：偏移底板 + 4–6° 倾角，随指针 ±4° | `components/layout/TiltPanel.vue` |
| 组件只有三种形态 | `primitives/Tag.vue`（实心块 / 描边块）、`primitives/DotLink.vue`（方点 + 文字） |
| 主操作全屏唯一：黑长条 + 反白字 + 强调色箭头 | `primitives/PrimaryAction.vue`，每屏只用一次 |
| 表格：无斑马纹、无竖线、表头实心块、行悬停反白 | `styles/forms.css` 的 `.rtable` |
| 图表：墨色单色 + 强调色高亮 1 个系列 | `components/archive/ClassChart.vue` |
| 逐字解码 32ms/字、尾部 3 个乱码位、只解码一次 | `primitives/DecodedText.vue` + `stores/decode.js` |
| 刻度动效（步进闪烁 / 匀速自转 / 定长倒计时） | `styles/motion.css`、`state/VerifyComplex.vue`、`state/FailureBlock.vue` |
| 幕切换单帧完成 + 300ms 故障撕裂 | `stores/curtain.js` 的 `flip()` + `components/fx/GlitchTear.vue` |
| 四态：常态 / 进行中 / 失败 / 成功 | `views/GateView.vue` + `components/state/*` |
| 空闲 45s、压暗 45%、455ms 呼吸、输入仅用于唤醒 | `components/state/IdleOverlay.vue` + `App.vue` |
| 响应式：1920×1080 基准等比缩放、画布反向撑开铺满 | `composables/useViewport.js` |
| 窄屏 <900px：单列、字号 ×0.85、去竖轴/引线/倾角 | `useViewport.js` 的 `mode` + `base.css` 的 `.mode-column` |

---

## 二、页面结构（4 个路由，对应提示词「载体配方」）

| 路由 | 视图 | 载体配方 | 这一屏在演示什么 |
| --- | --- | --- | --- |
| `/` | `GateView.vue` | 登录 / 门禁 / 二次验证 | 四态全流程：准星进度复合体、失败黑板、成功抽离 |
| `/console` | `ConsoleView.vue` | 桌面仪表盘 | 三带 + 竖轴 + 22/40/38 分栏、登记簿、日志流、图表 |
| `/record/:id` | `RecordView.vue` | 后台表格 / 详情页 | 编号与时间戳、处理记录、关联表、复本申请 |
| `/spec` | `SpecView.vue` | 演示看板 | 把风格层本身当档案陈列：幕值、色值、字阶、三形态、四态、动效、验收 |

框架（品牌带 / 主带 / 状态带 / 竖轴 / 空闲遮罩 / 撕裂）在 `App.vue` 里，全站唯一，视图只填主带的内容。

---

## 三、状态管理（Pinia）

| Store | 职责 |
| --- | --- |
| `stores/curtain.js` | 幕值 0→1、`flip()` 触发单帧换色 + 撕裂遮盖 |
| `stores/session.js` | 四态 `phase`、阶段 `stage`（0–3，驱动标记块）、凭据校验与尝试次数、失败原因、空闲标记 |
| `stores/archive.js` | 登记簿数据、筛选、当前选中、日志流（每条都带时间戳出处） |
| `stores/decode.js` | 「同一段文字只解码一次」的登记簿 |

---

## 四、文件清单

```
archive-desk/
├─ index.html                 · 入口；预加载两套字体
├─ vite.config.js             · @ 别名、127.0.0.1、strictPort
├─ public/fonts/              · 自托管 woff2（可变字重，合计 ~70KB）
└─ src/
   ├─ main.js                 · 挂载 Vue / Pinia / Router，按序引入四份样式
   ├─ App.vue                 · 全局框架：三条横带 + 竖轴 + 撕裂 + 空闲遮罩；把幕值与字号倍数写回 :root
   ├─ router/index.js         · 4 条路由（hash 模式，静态托管可直接打开）
   ├─ data/registry.js        · 内容层唯一数据源：机构槽位、四阶段、签发凭据、9 卷档案
   ├─ utils/format.js         · 时间戳 / 日期的统一等宽格式
   ├─ composables/
   │  └─ useViewport.js       · 唯一的响应式实现：k = min(vw/1920, vh/1080)，画布反向撑开
   ├─ styles/
   │  ├─ tokens.css           · 设计令牌：两幕端点色、幕值插值、字号阶梯、时长四档
   │  ├─ base.css             · 复位、画布、三带、12 列、竖轴、排印工具类、窄屏降级
   │  ├─ forms.css            · 三种组件形态、主操作、表格、字段表、编号槽
   │  └─ motion.css           · 步进闪烁 / 匀速自转 / 逐行打印 / 撕裂 / 呼吸
   ├─ components/
   │  ├─ layout/              · BrandLockup 三行锁排 · ClockBlock 时钟 · StatusBand 状态带
   │  │                          AxisRail 竖轴与标记块 · TiltPanel 倾角主面板
   │  ├─ primitives/          · DecodedText 逐字解码 · Tag 两种块形态 · DotLink 方点文字
   │  │                          PrimaryAction 主操作 · FieldTable 档案字段表
   │  │                          SectionLabel 小节标签 · LeaderLine 1.2px 引线
   │  ├─ archive/             · RegistryTable 登记簿 · ArchiveCard 档案卡 · FilterRail 筛选
   │  │                          ClassChart 单色图表 · LogStream 日志流
   │  ├─ state/               · VerifyComplex 准星/进度复合体 · FailureBlock 失败黑板
   │  │                          IdleOverlay 空闲遮罩
   │  └─ fx/GlitchTear.vue    · 300ms 故障撕裂（横向块位移 + 色散 + 亮度跳变）
   └─ views/                  · GateView / ConsoleView / RecordView / SpecView
```

---

## 五、运行方式

需要 Node ≥ 18（实测 Node 22）。

```bash
cd archive-desk
npm install          # 已装过可跳过
npm run dev          # http://127.0.0.1:5273
```

其他命令：

```bash
npm run build        # 产物在 dist/
npm run preview      # 预览产物 http://127.0.0.1:5274
```

调试用参数（方便验收四态与双幕，不必手点）：

| 地址 | 效果 |
| --- | --- |
| `/#/?demo=working` | 直接进入「进行中」 |
| `/#/?demo=failure` | 直接进入「失败」（整屏翻墨幕） |
| `/#/?demo=success` | 直接进入「成功」 |
| `/#/console?ink=1` | 直接以墨幕打开 |

正常路径：门禁页点左侧任一「已签发凭据」→ 回车 → 核验 1.4s → 抽离 → 调阅厅。
故意输错（如 `0000`）→ 整屏翻墨幕 + 失败黑板，2.6s 后回常态并保留一行具体原因。

---

## 六、槽位与可调参数

换内容只改 `src/data/registry.js` 的 `org`：

```js
{ zh: '恒序档案署', en: 'PERPETUAL', en2: 'SYNTHESIS OF RECORDS', en3: 'ARCHIVAL DESK',
  mark: '∞', code: 'PR∞A', desk: 'EST. 1911' }
```

换形态只改 `src/styles/tokens.css`：`--c-paper-*` / `--c-ink-*` 八组端点色、`--accent` / `--alert`、`--t*` 阶梯、`--d-*` 四档时长、`--axis-x` 竖轴位置、`--band-*` 带高。

窄屏阈值在 `composables/useViewport.js` 的 `NARROW = 900`；空闲时长在 `state/IdleOverlay.vue` 的 `IDLE_MS = 45000`。

---

## 七、两处必要偏离（提示词内部互斥的地方）

1. **字段表字号**：第四节写「dt 弱色 13px / dd 墨色 14px」，但同一节又规定「字号阶梯不可自创 15.3px 这类中间值」，验收第 4 条也要求字号全部来自阶梯。按后者执行，取 **11 / 12.5px**。
2. **墨幕下的主操作**：第五节写「纯黑长条」，但墨幕底色就是纯黑，长条会消失。按第一节「两个色幕是同一套角色的两组取值」做角色反相——墨幕下长条转反白、字转墨色，悬停仍整条转强调色。不可用状态则改为描边块（形态 2），避免整块留白抢戏。

另：逐字解码只用在短文本（标签、编号、标题、卡片名）；成段中文按普通排印直出，否则一屏要等近两秒。

---

## 八、验收对照（对应提示词第九节）

| # | 条目 | 现状 |
| --- | --- | --- |
| 1 | 灰度下三级层级另成立 | 层级由字号/字重/实心块承担，去掉强调色仍可读 |
| 2 | 50% 缩放仍可辨认 | 品牌锁排 21/11/11、主操作 52 高、状态带 11px 加粗 |
| 3 | 彩色 ≤5%、仅两个色相 | 强调色只出现在光标、进度、当前项、标记块；警示色只在失败态 |
| 4 | 字号全部来自阶梯 | 只有 10 级（+112 幽灵字），窄屏整体 ×0.85 由 `--ts` 统一下发 |
| 5 | 三种形态、主操作唯一 | `Tag` 两种 + `DotLink` 一种；每屏只渲染一个 `PrimaryAction` |
| 6 | 文案 ×3 不破版 | 超长一律省略号 / `line-clamp`，不改字号 |
| 7 | hover 与焦点两态 | 全部可点元素都有 `:hover` 与 `:focus-visible`（2px 强调色、偏移 2px） |
| 8 | 四态 ≥3 处差异 | 整屏幕色、中央图形、主操作文案、状态带、标记块高度、字段值（尝试次数）都变 |
| 9 | 去掉插图仍成立 | 全站没有插图，唯一装饰是 6–7% 的幽灵字与点阵底板 |
| 10 | 无圆角/投影/图标库/emoji/感叹号 | 0 圆角、0 投影、图形全部为矩形与矩形斜接箭头 |
