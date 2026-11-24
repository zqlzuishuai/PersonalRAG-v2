# Web 前端开发与维护

## 现状与目标

现有 Vue 3 + Vue Router + Vite 应用保留 Rhine 登录与进入动画，登录后的资料工作区由 Vue 页面、Naive UI、Reka UI 和 Lucide 构成。Starlette 管理认证和业务 API，浏览器使用同源 `/api/*`。目前有登录、注册入口、资料库、详情及版本、正文检索、回收站；版本速览显示元数据，不是完整原文查看器。首版还需补齐**完整原文查看及在线编辑**与**带引用的问答及历史回看**，验收顺序见[产品计划](PRODUCT.md)。

| 流程 | 现有入口与状态 |
| --- | --- |
| 登录 → 资料库 | [router](../frontend/src/router/index.js) 用 `/api/auth/me` 守卫受保护页面；[App.vue](../frontend/src/App.vue) 管理工作区与登录交接。三个真实入口 `/library`、`/search`、`/trash` 和文档详情保留。 |
| 找资料 → 看版本 → 处理 | [LibraryView](../frontend/src/views/LibraryView.vue) 管理目录、筛选、上传、分页与速览；[DocumentView](../frontend/src/views/DocumentView.vue) 管理资料属性、版本、处理状态；列表按实际接口分页，不把本页数量当全库数量。 |
| 搜索 → 核对片段 | [SearchView](../frontend/src/views/SearchView.vue) 调用 `POST /api/search`，显示标题、版本、片段和资料详情入口。历史版本精确跳转、完整原文和问答来源跳转属于待交付功能。 |
| 回收 → 恢复 | [TrashView](../frontend/src/views/TrashView.vue) 使用现有资料/文件夹回收与恢复接口；不把资料批次恢复当作任意多选批量操作。 |

## 开发、预览与构建

Node 版本范围见 [package.json](../frontend/package.json)，本地真实 API 默认由 Vite 代理到 `127.0.0.1:8001`。正向业务测试先配置隔离环境；环境变量和启动方式见[产品计划](PRODUCT.md)。

在 `frontend/` 执行：

```powershell
npm.cmd ci
npm.cmd run dev -- --configLoader native
npm.cmd test
npm.cmd run build -- --configLoader native
```

仅检查 UI 时，先构建，再从仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe -B frontend/tests/preview_server.py
```

打开 `http://127.0.0.1:5188/login`，隔离账号 `preview / preview`。`preview-expired` 和 `preview-unavailable` 使用同一示例密码，用于模拟会话 401 和 503。预览是内存 API，不连接数据库或模型，未模拟操作返回 501；结束用 Ctrl+C。

## 关键实现和维护规则

- 样式入口 [main.js](../frontend/src/main.js)：`rhine.css` → `rhine-motion.css` → `rhine-responsive.css` → `workspace.css`。三维资源、本地字体、许可证与上游署名见[前端说明](../frontend/README.md)和[第三方声明](../frontend/THIRD_PARTY_NOTICES.md)。早期蓝色、Ink Wash 外观已被当前工作区替代。
- 登录逻辑以真实认证及会话守卫为准；三维仅负责呈现。`components/rhine/` 中 `Stage.ts`、着色器、`useRhineMotion`、`motionMath` 和 `loginTransition` 管理场景、逐帧几何和交接。成功时保留原登录层及同一份资料库 DOM，约 1230ms 后交接，不截图或重挂载资料库；视口中途变化完成交接，减少动态效果或无 WebGL 使用静态降级。紧凑模式保留可用的表单、原生滚动和 16px 输入。
- [WorkOverlay](../frontend/src/components/WorkOverlay.vue) 复用 Reka 的焦点、读屏标题及遮罩机制；保存期间锁定关闭，未保存时离开要确认。使用现有打开状态与挂载方式；变更退场要先确认关闭状态真的传到 Reka，不用一层 Vue Transition 掩盖生命周期问题。路由进入动画按 `route.path` 区分，目录 query 变化不重新播放；登录交接期间不叠加页面过渡。
- [folderCache.js](../frontend/src/data/folderCache.js) 复用并发目录请求，缓存空和非空结果，失败可重试；手动刷新或目录写入后失效。同条件刷新保留已显示行；只变筛选条件不额外加载目录树。Skeleton 的列宽和行高应与实际表格对齐，注意全局 `[role='status']` 样式。
- 继续用当前布局和组件交付原文与问答。原文默认作为文本展示；若增加 Markdown 渲染，限制不可信 HTML/链接。保留未保存文字、版本冲突提示、明确的模型失败状态和键盘操作；别伪造后台处理进度、全库计数和未接通的操作。

## 验收与发布

- 本地回归看测试和构建；浏览器实测至少覆盖桌面及窄屏、键盘焦点、慢请求、未保存离开、减少动态效果。验证首版新功能时另用两名测试账号和真实后端，完成[联合验收](PRODUCT.md)中的原文编辑、发布、搜索及问答。
- 历史证据：11 月 8 日内存预览覆盖登录、工作区导航、窗口保护、宽窄布局与部分错误态，不能证明真实数据库写入或实机软键盘。历史公网发布验证过页面/资源和认证后的读取、正文搜索；未演练回滚，未完成浏览器写入闭环。发布号、截图和请求记录见[部署交接](../HANDOFF.md)。
- 发布前构建对应前端源码包，在 `frontend/` 用项目 Python 环境执行 `python scripts/package_source.py`。保留许可证和对应源码，不能包含 `.env`、私有资料或后端密钥；用实际构建的文件名核对下载，历史发布曾因固定 ZIP 名命中 CDN 旧缓存。服务器构建、版本、校验和回退详见[部署交接](../HANDOFF.md)。
