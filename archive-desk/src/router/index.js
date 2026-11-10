import { createRouter, createWebHashHistory } from 'vue-router'

/**
 * router/index.js
 * 四个视图对应提示词「载体配方」里的四种载体：
 * /        门禁 / 二次验证（四态的主战场）
 * /console 桌面仪表盘（三带 + 竖轴 + 分栏 + 档案表）
 * /record  后台详情页（表格规则、编号与时间戳）
 * /spec    形式规范（把风格层本身当作一份档案来陈列）
 * 用 hash 路由：静态托管到任意目录都能直接打开，无需服务端 rewrite。
 */
const routes = [
  {
    path: '/',
    name: 'gate',
    component: () => import('@/views/GateView.vue'),
    meta: { title: 'GATE · 门禁', stage: 0, idle: true },
  },
  {
    path: '/console',
    name: 'console',
    component: () => import('@/views/ConsoleView.vue'),
    meta: { title: 'CONSOLE · 调阅厅', stage: 1, idle: true },
  },
  {
    path: '/record/:id',
    name: 'record',
    component: () => import('@/views/RecordView.vue'),
    props: true,
    meta: { title: 'RECORD · 档案', stage: 2, idle: false },
  },
  {
    path: '/spec',
    name: 'spec',
    component: () => import('@/views/SpecView.vue'),
    meta: { title: 'SPEC · 形式规范', stage: 3, idle: false },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  const base = '恒序档案署 · PERPETUAL ARCHIVE'
  document.title = to.meta?.title ? `${to.meta.title} — ${base}` : base
})

export default router
