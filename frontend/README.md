# PersonalRAG Vue 前端

Vue 3 + Vue Router + Vite，使用现有 Starlette 同源 `/api/*`。Rhine 视觉移植自 [rhine-lock](https://github.com/tmc5csxr9m-cpu/rhine-lock)，具体来源与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 开发与构建

在此目录运行（Node 版本要求见 package.json）：

```powershell
npm.cmd install
npm.cmd run dev -- --configLoader native
npm.cmd test
npm.cmd run build -- --configLoader native
```

开发服务把 `/api` 代理到 `127.0.0.1:8001`。正式构建生成 `dist/`，由项目的 `web_frontend.py` 提供页面与 `/assets/*`。字体、纹理、图标与许可证全部位于 `public/assets/`，无运行时外部字体服务。

## 隔离界面预览

先构建，然后从项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -B frontend/tests/preview_server.py
```

打开 `http://127.0.0.1:5188/login`，示例用户名与密码均为 `preview`。
这是**内存示例 API**，仅用于界面检查，不能处理真实资料，不连接数据库或模型。
支持登录、列表、标题筛选、详情、检索示例和回收恢复；未模拟的操作返回 501。
按 Ctrl+C 结束，内存中的变更随进程清除。

需要检查登录成功后会话校验失败的恢复路径时，可用 `preview-expired / preview`（会话401）或 `preview-unavailable / preview`（会话503）；这两个也是隔离测试账号。

## 移植结构

- `src/components/rhine/`：Vue 标志、时钟与三维生命周期适配。
- `src/components/rhine/scene/`：上游 Three.js 场景与着色器；登录页延迟加载。
- `src/rhine.css`：当前全站样式。原 `styles.css` 作为前一版样式保留，当前未导入。
- `src/workspace.css`：登录后资料工作区的新视觉层，按 Ludi B端规范组织列表、字段、状态与窗口；覆盖旧工作区样式，登录样式保持独立。
- `src/components/WorkOverlay.vue`：基于 Reka UI 的统一窗口，400px 对话框、600px 抽屉、手机底部面板；处理焦点、遮罩、脏数据和提交期间的关闭保护。
- `src/rhine-motion.css`：横屏 1920×1080 设计坐标、入场、准星与真实页面卡片飞行样式。
- `src/rhine-responsive.css`：竖屏、窄屏及低于 620px 的短横屏，原生尺寸表单、安全区与自然滚动。
- `src/views/`：原有登录、资料、详情、检索和回收业务页面。
- `tests/login.test.mjs`：编译真实登录 SFC 验证 HTTP 状态与重试，使用模拟 HTTP 边界。
- `tests/scene.test.mjs`：编译实际 Stage，验证网格、灯光阴影及渲染器显式释放与幂等性，不测量真实 GPU 内存。
- `src/components/rhine/motionMath.js`：直接适配上游 SnapCard 等比指数缩放、二次弧线路径、透视、阴影和入场/退场采样函数。
- `src/components/rhine/loginTransition.js`：受认证守卫保护的真实目标页面准备、按帧卡片飞行和取消；`archiveTransition.js` 只保存短暂呈现状态，不保存凭据或资料。
- `src/components/rhine/useRhineMotion.js`：描标、分层显现、验证进度、错误切换与三维解体的协调。
- `RhineDecodeText.vue` / `decodeText.js`：逐字解码与最多三个扰动字形；隐藏页面、减少动态效果及卸载时停止。
- `RhineCallouts.vue`：随真实三维投影变化的标注引线；紧凑布局隐藏装饰引线。

三维场景可暂停，后台停止，离开登录页释放；减少动态效果或 WebGL 不可用时显示静态 SVG。真实认证仍完全由 `/api/auth/login` 决定。

登录入场使用上游无桌面截图分支：先描标，再组装雕塑和分层显现界面。成功后先通过会话守卫准备真实资料库，保持登录组件和 GPU 场景挂载约 1230ms，目标页面按上游 SnapCard 公式飞行；结束后同一份资料库 DOM 接管，避免截图替换或重新挂载闪烁。没有使用 View Transition 或横纵独立缩放。减少动态效果时直接交接，途中启用也会结束大幅运动。会话守卫拒绝进入、浏览器返回、离页后迟到的登录响应均有回归覆盖。

紧凑布局从可见标本卡的 DOM 矩形出发，保持原版等比飞行公式。飞行中改变视口尺寸会直接完成交接，避免使用旧尺寸拉伸。紧凑布局输入框至少 16px；粗指针设备及紧凑入口使用低质量三维、30fps 和不高于 1.25 的像素比。

登录表单使用布局缩放而非整层 3D 栅格缩放；静止文字无 transform，桌面输入实际显示至少16px。玻璃装饰层单独保留透视，成功退场和资料库飞行不变。

当前前端回归 19 项。浏览器检查覆盖 320、375、430、768、844、999、1024、1440px，以及竖屏成功进入、中途旋转、缩小输入视口和减少动态效果；没有实机验证手机软键盘。详情证据与范围见项目 HANDOFF。

当前构建的三维独立块约 785 kB（gzip 约 241 kB），会产生 Vite 体积提示；没有把这部分加载进资料库入口块。部分显卡驱动会对上游着色器发出编译警告。

2026-11-08 已将本版部署至 https://rag.191226269.xyz ，连接服务器现有同源后端。用户手动登录后，会话、真实资料与版本、检索、回收站读取均实测成功；本轮没有进行真实上传处理或回收恢复写入。发布版本、回滚和证据见项目 HANDOFF.md。

## B端工作区

2026-11-08 按用户指定的 [Ludi B端设计 skill](https://github.com/Ludi-Herry/b-end-design-system-skill) 重做登录后工作区，保留 Rhine 登录与进入动画。资料名称打开右侧速览，管理版本保留独立 URL；上传和移动使用抽屉，新建/改名与回收确认使用小窗口。标题、标签、筛选范围和分页仍调用原 API。全库总数、批量操作和处理百分比未获接口支持，因此没有伪造相关控件或数据。

新增 `reka-ui` 和 `lucide-vue-next`。19 项既有前端回归与构建通过；真实浏览器另外检查了窗口保护、同路由目录后退、低速提交锁定、标题保存及复原、上传错误、检索与回收站显示、320–1440px 布局、减少动态效果。所有浏览器业务操作均使用内存示例 API，不代表真实数据库/模型或公网验收。

发布时在生产构建后运行 `python scripts/package_source.py`，生成 `/assets/source/personalrag-frontend-source.zip`。登录页与工作区页脚提供下载，以提供该构建对应的前端源码。打包使用明确的前端路径白名单，不包含 `.env`、后端、数据库、真实资料或 node_modules。

部署验收补充：本版发布号为 `20261108-163302`。上述隔离示例说明仍适用于本地5188预览；公网使用真实后端和原有账号。正式发布包是构建时固定快照，后续文档修订不自动更新服务器。
