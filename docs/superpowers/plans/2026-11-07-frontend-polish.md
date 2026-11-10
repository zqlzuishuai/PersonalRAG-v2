# PersonalRAG 前端界面实施计划

依据 HANDOFF.md 中已确认的 Vue 3 业务范围，完善已有五个页面的视觉与导航。仅修改本地前端，保留已有 API 与业务操作，不部署到服务器。

设计：深蓝 #172741 侧栏、浅灰 #f5f7fb 工作区、蓝色 #345dd7 主操作、白色内容区、灰色 #6b778c 辅助信息。使用系统中文字体，无外部字体或新增依赖。资料以文件行和文件夹展示，避免虚构统计数据。

- [x] 读取 handoff，对照实际页面与 HTTP 接口，保留工作区已有改动。
- [x] App.vue 增加跨页面侧栏与退出入口；components/AppIcon.vue 提供统一图标。
- [x] styles.css 提供全局视觉、键盘焦点、窄屏布局；移除页面重复的 scoped 样式。
- [x] LoginViews.vue 完善登录布局；LibraryView.vue 完善上传、筛选、目录和资料列表；SearchView.vue 完善搜索与来源展示；详情与回收站应用统一样式。
- [x] 构建前端，验证页面编译；本地浏览器检查布局和导航，记录验证边界。

验证命令：frontend 目录中执行 npm.cmd run build -- --configLoader native。浏览器检查不代表生产数据库和模型业务流程验收。

验证记录：生产构建成功，28 个模块。临时模拟 API 隔离真实数据库，浏览器检查了资料列表、文件夹编辑入口、标题筛选与空状态、清除筛选、详情跳转、标题编辑入口、最新上传和当前可检索标记、检索片段与来源、回收站切换、退出跳转。390 × 844 视口下检查资料库、登录与回收站；登录和资料库的 scrollWidth 不超过 innerWidth。模拟页面控制台未记录 warn/error。发现页面切换继承滚动位置，已在 router 中增加 scrollBehavior。

不包含：真实账号登录、上传、数据库写入、真实模型处理和公网部署。验证截图保存在本次 Codex artifact 目录。测试服务和模拟脚本在结束时清理；再次预览在 frontend 运行 npm.cmd run dev -- --configLoader native，业务接口仍需本地 8001 后端。
