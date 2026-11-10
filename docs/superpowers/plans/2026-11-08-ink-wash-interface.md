# PersonalRAG 水墨界面重做

## 设计与范围

使用 frontend-design 与 ui-ux-pro-max。用户已指定 Ink Wash 方向，直接按该设计实现。保留 Vue 3、既有同源 API 和五个页面的业务流程，仅修改本地界面。

宣纸 #f8f5f0 / #f3efe8，墨色 #2c2c2c，苔绿 #6b7b6e、茶褐 #a89279、砂色 #c4b9a8。全站使用宋体 / 衬线字体栈。正文辅助信息采用更深的中性色，避免自然色在小字上对比不足。分隔线采用 20% 墨色，表单下划线加深以辨识输入位置。

横向导航与大幅留白替代深色侧栏。桌面页面上下 128px 留白，移动端 80–96px。移除登录装饰图形；标题与文字承担视觉表达。文件夹、资料列表和详情以细线分区，无卡片堆叠或重阴影。上传与筛选使用原生 details/summary 展开，支持键盘操作和筛选启用状态。

颜色、背景与边框以 800ms ease-in-out 变化；悬停微弱扩散阴影为 1000ms，按下以内阴影表达，不使用位移或缩放。焦点提示即时出现。prefers-reduced-motion 时关闭过渡与动画。

ui-ux-pro-max 的初次设计系统结果偏向通用落地页及瑞士风，第二次明确查询 ink wash 只得到 E-Ink/Paper 近似结果；其无动画建议与用户明确要求不一致。因此视觉以用户要求为准，仅使用匹配的阅读、可见焦点及 reduced-motion 指引。未引入字体服务、图像、动画库或表单依赖。

## 实施与验证

- [x] 修改 App.vue 全局外壳与 LoginViews.vue 登录布局。
- [x] 重写 styles.css 设计变量、页面布局、响应式和交互状态。
- [x] LibraryView.vue 展开工具区；SearchView.vue、TrashView.vue 和详情应用统一风格。
- [x] npm.cmd run build -- --configLoader native：28 modules transformed，构建成功。
- [x] 本地隔离模拟 API，浏览器检查导航、工具展开、筛选空状态及启用提示、清除筛选、检索来源、详情版本标记、回收站切换及模拟恢复、退出跳转和登录 401 错误状态。
- [x] 检查窄屏、键盘焦点、减少动态效果和文字对比度，保存截图。

## 本轮实测

- 资料库 1440、1024、768、375px 视口检查；375px 同时展开上传与筛选仍无横向溢出。1024 / 768 / 375px 实测 scrollWidth 分别为 1009 / 753 / 360px。
- Enter 可以操作原生 summary，Tab 可到下一个工具区，键盘焦点 outline 为 solid。
- 普通模式过渡为 0.8s / 1s，按钮 transform 为 none；模拟 prefers-reduced-motion: reduce 后 summary 和按钮过渡均为 0s，退出模拟后恢复普通模式。
- 核心正文、辅助文字、状态、标签、错误文字在两种宣纸背景上对比度均 >= 4.5:1，最低 4.60:1。苔绿、茶褐与砂色保留为强调色变量；低对比自然色不用于小号正文。
- 移动登录隐藏说明性大标题，仅保留账号表单；375px 下未发现横向溢出。桌面保留双栏和充分留白。
- 最后一次浏览器控制台检查未出现 warn/error。
- 截图位于本轮 artifact 目录的 ink-wash/：login-desktop.jpg、login-mobile.jpg、library-desktop.jpg、library-mobile.jpg。截图使用明确标注的示例资料，不含真实用户内容。

验收服务和脚本在结束时清理。实际开发预览仍在 frontend 目录运行 `npm.cmd run dev -- --configLoader native`，业务接口代理到本地 8001 后端。

范围边界：本轮不进行公网部署，不写入真实资料，不将模拟接口验收视为真实模型或数据库业务验证。
