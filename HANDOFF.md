# PersonalRAG v2 Handoff

更新日期 2026-11-09，时区 Asia/Hong_Kong。

## 2026-11-09 加载占位与目录重复请求已修复并上线（最新）

版本 `20261109-133233`，入口 https://rag.191226269.xyz/library 。

- 首屏改为静态Naive UI表格骨架及低对比目录占位；同条件刷新保留旧内容、数量及高度，失败保留旧内容并提示。登录/Rhine文件未改。
- 目录树改为目录版本驱动刷新；30秒页面实例内目录缓存，合并并发读取，空结果同样缓存。手动刷新和目录写成功清空缓存，旧响应不能覆盖新数据。资料本身不做跨查询缓存。
- 22项前端测试及构建通过。隔离两秒延迟下保留8行；筛选不再重查目录；隔离新建目录后立即刷新。生产首屏auth/me、documents、folders各1次；手动刷新documents/folders各1次；后续筛选只有documents1次，均200，控制台无错误。账号为空，无生产资料写入。
- 空用户只读探测：目录SQL中位1.75ms，含建连事务16.1ms；浏览器首屏接口TTFB约492–513ms，先前刷新/筛选约916–1137ms。不能据此推断有数据或全文检索查询耗时；未改数据库/后端。
- 本次87文件校验，后端/.env与PID1401257不变；当前23个公网资源/页面验证通过。为绕过固定源码ZIP的CDN旧缓存，工作区下载使用构建哈希文件名：https://rag.191226269.xyz/assets/source/personalrag-frontend-source-index-Do5rs9Ai.zip 。
- 回滚：`/root/personalrag-v2/app/.venv/bin/python /root/personalrag-v2/releases/frontend-20261109-133233/rollback.py`。备份在同目录before-frontend.tar.gz，回滚未演练。中间发布132900被本版取代但备份/审计保留。
- 证据与逐文件行号：`C:\Users\茶鸣拾贰率\.codex\visualizations\2026\11\09\deploy-20261109-133233`，另有 `loading-request-fix/` 慢请求截图、原代码快照及请求计数。设备目录已更新并备份。

## 2026-11-09 Naive UI 主界面与标签多选已部署（历史发布）

用户授权部署当前前端。生产入口 https://rag.191226269.xyz ，版本 `20261109-130750`。

- 发布83个前端文件及对应源码包、许可；后端与.env哈希未变，服务PID1401257保持，API健康。未上传本地演示服务、真实资料或本地配置。
- 19项既有前端测试及构建通过。公网19个静态文件SHA256一致；4个HTML入口去除Cloudflare自动注入的统计脚本及标签间空白后与构建一致。
- 用户手动登录后，会话、目录、当前目录/全库资料、tag=RAG筛选均200，浏览器error/warn为空。账号全库返回0份资料；有资料时的多标签正向匹配只在本地示例验证。已重置筛选，保留公网资料库标签。
- 没有新增/修改/删除生产资料，没有做上传、处理、回收或恢复写入验收。
- 回滚：`/root/personalrag-v2/app/.venv/bin/python /root/personalrag-v2/releases/frontend-20261109-130750/rollback.py`；旧前端备份在同目录 `before-frontend.tar.gz`。回滚未实际演练。
- 部署证据：`C:\Users\茶鸣拾贰率\.codex\visualizations\2026\11\09\deploy-20261109-130750`。设备目录已增量更新并保留旧发布记录及原目录备份。

## 2026-11-08 新前端已部署并接通生产后端（历史发布）

用户明确要求把当前版本部署到服务器并连接后端，随后选择自己在公网浏览器登录，已完成手动登录。本次生产入口为 https://rag.191226269.xyz ，不再只是内存演示。下面此前各轮“未上线”的描述是各自当时状态。

- 发布版本 `20261108-163302`，上传包SHA256 `4f71f001a60cba5b221d32d3bc303cd54291d569f415b0ef9301804bb98209a8`，77个文件逐项校验。只发布 `frontend/` 白名单源码、依赖清单、静态产物和许可，没有上传本地.env、数据库、真实资料、node_modules或修改Python业务代码。
- 服务器仍为 `/root/personalrag-v2/app`、`personalrag-v2-web.service`、`127.0.0.1:8001`。SSH使用已有本机Ed25519密钥，匹配known_hosts中的已固定主机密钥。后端在发布前已active；生产.env和Python文件哈希前后保持一致，PID1201561没有变化，不需要重启。
- 先增量发布资源，再原子替换dist/index.html；保留旧哈希资源供已打开的页面使用。旧前端完整备份在 `/root/personalrag-v2/releases/frontend-20261108-163302/before-frontend.tar.gz`。该目录保留上传包、manifest、发布结果与rollback.py，已清理staged临时副本。
- 如需回滚，由root运行 `/root/personalrag-v2/app/.venv/bin/python /root/personalrag-v2/releases/frontend-20261108-163302/rollback.py`；恢复旧前端文件和入口，保留新资源以兼容打开中的页面。回滚脚本已准备，未实际执行回滚演练。
- 登录及工作区页脚新增“前端源码”。`frontend/scripts/package_source.py` 在构建后生成白名单源码ZIP，本次58个源文件且ZIP完整性通过，不包含.env、后端配置或真实资料。公网 `/assets/source/personalrag-frontend-source.zip` 可下载；构建后必须重新运行打包脚本再发布。

本次新鲜证据：19项前端回归通过，Vite构建通过。公网HTTPS证书正常校验，index及全部17项静态资源/字体/纹理/许可/源码ZIP返回200且SHA256与本地发布包一致；JS MIME为application/javascript。深层页面200；未登录auth/me、documents、folders为401，私有.env和未知API为404；一次不存在账号的登录请求返回401，无500。

用户手动登录后，实际公网浏览器读取真实资料（本页2份），auth/me、documents、folders、资料详情、versions、processing-runs、trash/documents、trash/folders均200；速览及版本历史正常。POST /api/search 返回200，查询“知识管理”显示5个真实片段。未保存、输出或代填用户密码。最终浏览器JS error为空，发布后服务日志65行中无ERROR/Traceback。

本轮没有新增、改名、上传、处理、回收或恢复真实资料；没有验证重启恢复、完整上传处理写入闭环、历史原文完整性或长期稳定性。用户已登录的公网标签保留在资料库；没有替用户退出。

设备目录仅增量更新阿里云“PersonalRAG v2 Web”服务条目，保留其他设备与凭据，旁边保存原目录备份。部署报告和公网截图位于本次产物目录 `deploy-20261108-163302/`，含manifest.json、result.json、public-verification.json、authenticated-browser-checks.json、server-final-check.json、production-library.png及上传包；这是发布时固定快照，后续本地文档变化不等于再次部署。

## 2026-11-08 Ludi B端工作区重设计（最新）

用户指定 https://github.com/Ludi-Herry/b-end-design-system-skill ，并明确选择“保留登录动画，重做登录后工作区”。已读取 commit f56256e 的 SKILL.md 与 references/01–07；前端仍为 Vue + 同源原API，Rhine登录和飞行动画保留，没有部署公网。

- 新增 `frontend/src/workspace.css`：浅灰绿画布、白表面、语义绿色、细边框与统一字阶；独立覆写工作区，原登录样式保持。资料库使用页头→内联筛选→列表/分页，时间右对齐，主操作唯一，状态浅底深字，不伪造总数。
- `WorkOverlay.vue` 基于成熟 Reka UI Dialog 原语，实现400px小窗口、600px右侧抽屉、手机80dvh底部面板，内部滚动、固定底栏、焦点锁定/返回。遮罩不关，脏数据关闭/浏览器后退确认，提交时退出锁定；支持路由离开和同记录query/params更新。认证失效允许返回登录。
- LibraryView：资料名称打开速览并读取版本API；管理版本保留独立URL；新建/改名使用小窗口，上传/移动使用抽屉，文件夹回收明确可恢复影响。异步速览有请求序号保护。
- DocumentView：资料信息与版本历史区块，改名、标签、移动、上传版本和回收接入统一窗口；原业务请求与处理轮询保留。检索和回收站沿用原行为，统一新样式。
- App外壳改为紧凑导航与顶栏，工作区图标统一Lucide。新增依赖reka-ui2.11.0、lucide-vue-next0.577.0；对应许可及Ludi MIT声明保留。主JS约200kB/gzip71.5kB，三维独立块约785kB体积提示保留。

验证：19项既有前端回归通过、最终Vite构建通过。Ludi脚本扫描15个Vue文件未匹配违规（只有5条正则规则，不等于全部设计门禁证明）。独立只读复核提出的query/params更新保护、放弃按钮绕过busy、上传dirty残留均已修复并复核通过。前端定向diff空白检查通过。

实际浏览器：正常Rhine登录/飞行至新工作区，速览/详情导航，标题窗口保存并恢复原值；遮罩点击不关闭，Esc提示保留修改，Tab循环与关闭返回焦点；浏览器后退到不同目录query时出现确认，取消后输入保留；人工1200ms网络延迟下隐式Enter提交，关闭/放弃按钮均禁用，成功后恢复网络。上传遇到预览501仍可见错误并重试，放弃后重开不再误报dirty。320/375/768/1024/1440px无横向溢出；手机底部面板与检索/回收站展示正常，减少动态效果下窗口animation=none，最终浏览器JS error/warn为空。

所有业务浏览器验证使用隔离内存API，未验证真实数据库、模型、上传处理或公网；403部分受限场景及真机软键盘未验。后端没有支持的批量操作、全库总数和处理百分比没有伪造。临时上传样本已删除，示例标题恢复，媒体/网络/视口覆盖已清除。预览继续运行于 http://127.0.0.1:5188/login ，账号preview / preview，标签留在资料库。

来源和实现见 `frontend/THIRD_PARTY_NOTICES.md`、`docs/superpowers/plans/2026-11-08-b-end-workspace.md`。截图在既有产物目录 `b-end-workspace/`，`library-desktop.png`、`detail-drawer.png`、`create-modal.png` 展示最终设计；`before-b-end-workspace.zip`为修改前源码快照。未自动提交，原有大量未提交修改保留。

## 2026-11-08 登录表单清晰度修复（最新）

用户明确反馈浏览器内的登录文字和表单发糊。实际检查 1440×810：原面板 `scale(.7421875)` 叠加 rotateY/rotateX，整份文字进入 3D 合成层；输入 16px 实际显示约 11.875px，形成缩小和透视重采样。

- `rhine-motion.css` 将面板的尺寸适配改为布局 `zoom`，静止表单 transform=none，输入字形实际显示至少 16px；提高标签、说明和密码切换文字的最低显示字号。
- `LoginViews.vue` 增加 aria-hidden 的 `profile-surface`，仅玻璃装饰层保留跟随指针的透视和背景模糊，表单保留退场位移。整个 login-layout 层级高于三维引线，避免装饰盖住资料类型文字。
- `rhine-responsive.css` 明确紧凑布局 zoom=1、静止无 transform，并覆盖桌面字号下限；错误状态上移桌面面板，给提示预留空间，避免与页脚重叠。

19 项回归通过，最终构建通过，前端定向 diff --check 通过。实际浏览器检查 1024×768、1366×768、1440×810、1920×1080、2560×1080、1085×612、375×812：静止表单无变换、无横向溢出，输入实际显示至少16px。1366px 错误后面板 bottom=675、footer top=699.25，输入命中正常；失败重试成功，观察到卡片飞行和面板退场，最终登录层卸载、资料库接管。未更改业务接口或部署公网。

原始 PNG 对照 `clarity-fix/before.png`、`after.png`，尺寸和飞行状态记录位于既有产物目录的 `clarity-fix/`。本地预览已提供新构建；临时 CSS 对照随刷新清除，视口覆盖恢复，预览标签保留。

## 2026-11-08 补齐竖屏与剩余网页动效（当前状态）

用户认可横屏重做后要求“补齐剩下的”，并再次要求继续。本轮保持已认可的桌面几何与时点，补充网页范围内的响应布局和原版视觉细节；没有修改生产 API、数据库、模型或公网部署。

- 新增 `frontend/src/rhine-responsive.css`：竖屏、宽度不足 1000px 或高度不足 620px 时使用自然滚动布局；表单保持原生尺寸、16px 输入、48px 以上操作区域和安全区留白。普通横屏继续原设计坐标。
- 紧凑布局从实际标本卡 DOMRect 计算飞行起点，仍使用相同等比 SnapCard 公式。成功后先收起输入焦点并回到顶部；动画中视口尺寸变化超过 2px 时立即完成交接，清除 inert 和保留登录层。
- 新增 DecodeText 字形解码，验证/成功文本、描标信息接入；失败警告采用上游三角标、边条和四行逐次显现，显示真实提交次数。补齐三维投影引线和交点标识，紧凑布局隐藏装饰引线。减少动态效果时文字直接显示。
- 紧凑入口或粗指针设备限制三维为低质量、30fps、DPR≤1.25；保留暂停、后台停帧和卸载释放。实测发现静态 SVG 回退没有投影坐标时警告会定位到左上角，已改为静态雕塑中心，WebGL 丢失或切换减少动态效果时清除旧投影。

本轮验证：19 项前端回归全部通过，Vite 构建通过（51 modules）。新增紧凑断点/卡片起点、动画中旋转、字形解码回归。实际浏览器检查 320×568、375×812、430×932、768×1024、844×390、999×700、1024×768、1440×810，没有横向溢出；375px 进入录制 65 帧，飞行内容及最终资料库宽度均为 360px。中途旋转实测 active 登录层清除，最终资料库可用；缩小输入视口后密码焦点保留、输入字体 16px。没有实机手机软键盘证据。

在隔离示例 API 下再次检查 320px 上传/筛选展开、筛选空状态及清除、详情标签编辑入口/版本标记、检索来源、回收站类别切换和退出；这些不代表真实上传、编辑保存、模型处理或恢复验收。减少动态效果下四行警告 opacity 均为 1，重试成功后 login=false、inert=false；桌面两条实际投影引线和键盘焦点正常，最终浏览器 error 日志为空。当前三维独立块仍约 785kB（gzip241kB），保留构建体积提示。

本轮独立复核因代理使用限额未能执行，不能当作通过；已自行检查新增组件和生命周期。上一轮横屏的独立复核证据仅属于上一轮。

截图、竖屏采样及录制位于既有产物目录的 `responsive-finish/`；桌面最终图为 `desktop-complete.jpg`，竖屏为 `login-portrait-final.jpg`。最新构建已由本地预览提供，仍可访问 http://127.0.0.1:5188/login，示例账号 preview / preview。浏览器媒体仿真和视口覆盖已恢复，预览标签保留；服务按用户查看要求保持运行。详细实现记录见 `docs/superpowers/plans/2026-11-08-rhine-responsive-finish.md`。

## 2026-11-08 横屏切换重做（取代上一段 View Transition 方案）

用户再次指出动画与原项目差距很大，并明确“先只适配横屏”。本轮完整阅读上游 `transition.ts`、`App.svelte` 入场/逐帧/退场、BootOverlay/AuthRing 等组件，并解码仓库 `docs/media/lock-unlock.webp`（102帧、5.65s）对照。确认上一版的非等比缩放、直线插值、提前卸载 GPU 场景都偏离原实现。

- `motionMath.js` 直接适配原始 SnapCard 公式：单一指数缩放、二次 Bézier 中心路径、sin 驱动的 -13° 透视倾斜、按比例变化的圆角/阴影，以及 180/220/380/560/1220/1230ms 原时点。`tests/motion-math.test.mjs` 校验弧线、宽高比、全屏端点和时点。
- 移除上一版原生 View Transition 与 CSS 横纵缩放。App 显式保留 LoginView；认证通过并经过原路由会话守卫后，挂载真实 RouterView 资料库，将整幅实际页面作为固定/inert 的飞行卡片。登录 GPU 画布一直保留到退场结束，最后由同一个资料库 DOM 接管，业务接口没有修改。
- `useRhineMotion.js` 协调描标、分层显现、验证进度和三维解体；新增 RhineBoot、RhineReticle，准星跟随雕塑实际投影交点。无桌面截图时采用上游 plain 入场；没有伪造 OS 截图，也没有迁移 PAM/电源/音乐功能。
- `rhine-motion.css` 将横屏定位统一到 1920×1080 设计坐标。修正 CSS 缩放原点造成的面板偏移；用稳定滚动条留白及根元素实际矩形宽度，避免末帧因滚动条多出/少掉 15px。
- 保留减少动态效果；飞行途中启用也会直接交接。浏览器返回取消、守卫拒绝、离页后的迟到登录响应均做了清理；没有保存登录信息或资料快照。

本轮证据：前端 15 项回归通过，Vite 构建通过（47 modules）；独立只读复核确认几何公式/时点与上游一致、资料库实例在交接时保持。隔离示例 API 浏览器录制了入场 75 帧和最终退场 75 帧，退场期间 canvas 保持存在，结束后才卸载；目标样式宽度和最终实际宽度均为 1425px。检查 1920×1080、1366×768、1024×768、2560×1080 横屏：无横向溢出、提交按钮均在视口内；会话401回退可重试、减少动态效果无大幅飞行、最终 error 日志为空。

本轮只验收横屏，不声称竖屏完成。没有进行真实数据库、模型或公网流程。上游字体/材质及 AGPL 署名保留，源码来源版本仍为 a4df68c。

产物目录的 `landscape-motion/` 保存 `boot-samples.json`、`final-samples.json`、逐帧截图、横屏录制和 `ready-landscape.jpg`；`upstream-transition-contact.jpg` 是原项目演示逐帧对照。改动前快照 `before-landscape-motion.zip` 保留。隔离预览仍为 http://127.0.0.1:5188/login，正常示例账号 preview / preview，按查看要求保持运行。详细设计记录见 `docs/superpowers/plans/2026-11-08-rhine-landscape-motion.md`。

## 2026-11-08 补齐登录成功进入动画

用户指出前一轮遗漏上游成功后的动画。确实原 LoginViews.vue 在 POST 成功后直接 router.replace，本轮已修复：新增 granted 状态，按上游 exitFrame 节奏在 180ms 收起面板、220ms 调用雕塑 playDissolve(800)，560ms 开始将目标资料库画面从标本卡位置放大，持续 660ms。浏览器 View Transition 捕获真实目标页面，成功认证仍由原 API 决定。

- 新增 `frontend/src/components/rhine/loginTransition.js`，登录、RhineScene、全站 CSS 接入成功离场。手机端以档案面板位置作起点。支持取消尚未完成的延迟跳转，动画 API 失败时仍只导航一次。
- 减少动态效果直接进入；不支持 View Transition 的浏览器仍播放面板/雕塑离场，约 1150ms 后常规跳转。
- 复核发现登录 POST 成功但会话守卫又返回登录页时，原成功离场会留下隐藏表单。已检测最终路由，恢复 denied 状态、表单和雕塑，提示登录状态未能确认。新增 `Stage.resetDissolve()`。
- 前端回归现在 10 项通过，构建通过（42 modules）。新增成功延迟、取消、动画异常、减少动态效果、守卫重定向和场景恢复测试。没有修改生产认证策略、Python 业务接口或部署公网。
- 隔离示例 API 浏览器逐帧验证 `verifying → granted → 面板位移 → archive-opening → 资料库`，记录了 65 帧。测试会话 401 与 503 回退恢复、成功重试、减少动态效果直接进入、375px 卡片放大；最终 error 日志为空。
- `frontend/tests/preview_server.py` 增加测试账号 `preview-expired / preview`（登录成功后会话401）和 `preview-unavailable / preview`（会话503），仅为隔离内存测试。正常预览账号继续为 `preview / preview`。

动画证据在本轮产物目录 `login-transition/`，`success-entry.gif` 为按采样时间合成的录制；`samples.json` 和帧文件保留可核对状态。预览已重新运行在 `http://127.0.0.1:5188/login`（本轮执行 session 61543），按用户查看要求保留运行；浏览器测试标签留在正常登录页，媒体/视口设置已恢复。

## 2026-11-08 rhine-lock 前端移植（本地，当前界面）

用户要求读取 handoff 后，将 https://github.com/tmc5csxr9m-cpu/rhine-lock 移植为本项目兼容前端。本次在 `C:\PersonalRAG-v2/frontend` 实现，未部署公网。实际来源 commit 为 `a4df68c6bd9e01ecb7660659becf495957e57faa`。

- 保留 Vue 3、现有路由与全部业务接口，直接移植上游 Three.js `Stage.ts` / `shaders.ts`，没有引入 Svelte、Rust、PAM 或任何系统锁屏功能。已有 `lockscreen/`、`archive-desk/` 未修改。
- 新增 `src/components/rhine/`、`src/rhine.css`，登录为实时 ∞ 雕塑与人员档案玻璃面板，工作区为索引侧栏与灰白档案面板。登录请求驱动等待、验证中、黑橙错误、成功跳转；包含密码显示和暂停场景入口。
- 三维延迟加载，30fps 上限，窄屏使用低质量模式，后台停止、卸载释放，减少动态效果或 WebGL 不可用时显示静态 SVG。旧水墨 `styles.css` 保留，`main.js` 现在导入 `rhine.css`。
- 字体、纹理、图标、许可证全部在 `public/assets/`，与原 `/assets` 静态挂载兼容。新增 three、postprocessing、n8ao。上游 AGPL-3.0-or-later 和字体 OFL 许可保留于前端，来源说明见 `frontend/THIRD_PARTY_NOTICES.md`。将来网络发布时需提供修改版本对应源码。
- 实际生产静态路由在 Windows 下将 `.js` 当作 `text/plain`，浏览器出现空白。`web_frontend.py` 增加标准 JavaScript MIME 注册；`tests/test_web_frontend.py` 用错误 MIME 覆盖复现再验证修复。未修改认证或其他 Python 业务代码。

本轮证据：

- `npm.cmd test`：3 项回归通过。其中 2 项真实 SFC + 模拟 HTTP 边界的认证回归覆盖重复提交、401、403、网络失败、重试、成功与密码清空；1 项编译实际 Stage，验证网格、阴影与渲染器显式释放和幂等性。复核发现上游未显式释放灯光阴影，已先以失败测试复现，再补齐释放；不宣称测量过真实 GPU 内存。
- `npm.cmd run build -- --configLoader native`：41 modules，构建通过。主 JS 约 138 kB，独立三维块约 785 kB / gzip 241 kB，有体积提示；当前 Node 24.11.1 低于 package.json 声明版本，安装有 engine 提示，构建和测试实际成功。
- Python unittest discover：50 tests OK；不代表真实数据库/API 或公网验收。
- 使用原 `web_frontend.add_frontend_routes()` 加隔离内存示例 API，在浏览器检查等待/验证/错误/成功登录、暂停、筛选空状态、资料详情与最新/可检索标记、标签编辑入口、检索来源、回收站切换与恢复提示、退出。修正过错误主题的文字继承颜色。
- 检查 375、768、1024、1440px。375px 展开上传与筛选时无横向溢出，scrollWidth=360；768px 工作区为 753，1024px 登录为 1009。减少动态效果实测静态 SVG 可见、canvas 隐藏、transition=0s。
- 最终浏览器 error 日志为空；上游着色器在当前 Windows 驱动仍有梯度/浮点精度编译 warning，不宣称无警告。

完整计划和限制见 `docs/superpowers/plans/2026-11-08-rhine-frontend.md`。预览方式见 `frontend/README.md`。可复现的隔离预览脚本是 `frontend/tests/preview_server.py`，端口 5188、示例账号 `preview / preview`，不连接数据库或模型；未模拟操作返回 501。本轮验收进程会在结束时停止。

截图与改动前快照保留在：

`C:\Users\茶鸣拾贰率\.codex\visualizations\2026\11\08\01a1b97e-b9f6-7013-80e9-cb01fceb0fe3\`

其中 `rhine-preview/` 有登录及资料库桌面/手机截图，`frontend-before-rhine.zip` 是改动前前端快照。仓库原有未提交改动保留，没有自动提交。完整 git diff --check 仍发现原 auth.py / folder.py 尾随空格；本次改动的已跟踪前端文件定向检查通过。

临时 5188 预览服务已停止，浏览器测试标签已关闭并恢复视口/缓存设置。自动审批审查拒绝了删除本次产物目录下 `rhine-lock-source/` 临时源码副本的操作，仅返回 blocked by policy，未提供详细原因，因此副本保留，未尝试其他方式删除。

## 2026-11-08 水墨界面重做（本地）

用户明确指定 Ink Wash 风格，并要求使用 frontend-design 和 ui-ux-pro-max。本次替换前一版深蓝侧栏界面，保留 Vue 业务接口与功能；没有部署至公网。

- 宣纸背景 #f8f5f0 / #f3efe8、墨色 #2c2c2c、自然色变量、宋体 / 衬线字体栈。横向导航、大幅留白、20% 墨色分隔线，移除登录装饰图形和卡片样式。
- 交互采用 800ms 颜色与背景过渡、1000ms 微弱扩散阴影和按下内阴影，无位移或缩放；减少动态效果模式关闭过渡。
- 上传和筛选改为原生 details/summary 工具区；收起时仍显示筛选启用状态。移动登录页突出账号表单。
- 前端构建通过。隔离模拟 API 下检查了工具展开、键盘焦点、资料筛选、详情标记、检索来源、回收站切换和恢复提示、退出及登录错误状态。
- 响应式检查包含 375、768、1024、1440px；检查了 reduced-motion 和主要文字对比度。此结果不等于真实数据库/模型流程或公网验收。

设计和验证记录：`docs/superpowers/plans/2026-11-08-ink-wash-interface.md`。本地预览命令保持 `npm.cmd run dev -- --configLoader native`；后端仍需运行在本地 8001。

## 2026-11-07 本地前端界面更新

用户要求读取 handoff 后制作前端，本次在现有 Vue 页面上完善界面，没有重新实现后端或部署公网。

- `frontend/src/App.vue`：统一深蓝侧栏、导航、退出入口和页面外壳。
- `frontend/src/styles.css`、`components/AppIcon.vue`：统一视觉、中文系统字体、图标、键盘焦点及移动布局，没有新增依赖。
- 五个 views：登录双栏布局，上传与筛选区、文件夹与资料列表、正文检索及来源、详情版本和回收站统一样式；详情中的回收操作移到末尾。
- 路由增加滚动恢复，页面切换回到顶部，浏览器前进/后退恢复原位置。
- 构建通过；使用隔离模拟 API 在浏览器检查页面导航、筛选空状态、编辑入口、版本标记、检索来源、回收站切换与退出跳转。检查了桌面与 390px 窄屏布局。
- **此证据不代表真实业务或公网验收**。实际上传、处理、检索流程仍按原第 16 步验收。服务器仍是此前版本。

实施及验证记录：`docs/superpowers/plans/2026-11-07-frontend-polish.md`。本地预览：在 frontend 运行 `npm.cmd run dev -- --configLoader native`，业务 API 仍代理至 `127.0.0.1:8001`。

## 接手先读

项目已部署到 https://rag.191226269.xyz 。最近一次公网实测通过了健康检查、页面路由、测试账号登录、会话、资料与文件夹列表、退出登录。完整的公网浏览器业务验收仍待完成。

本地项目是 C:\PersonalRAG-v2，当前 Codex 工作区可能仍是 C:\PersonalRAG。先核实目录和写入权限。工作区已有大量未提交的用户与助手改动，保留这些改动。当前 Git HEAD 是 92a9e00，提交说明 initial commit，不能据此代表当前实现。

用户正在学习 LangChain/LangGraph。通常用户写后端，助手检查并实现 Vue 前端。用户说“下一步”时给一个具体阶段及验收要求，用户明确说“帮我写”时直接实现该阶段。检查时区分静态检查、模拟依赖测试、真实数据库/API 测试与公网浏览器验收。

凭据保留在各环境的 .env 和设备目录中。本文件不记录密码、API key、令牌或私钥。

## 已确认的首版范围

- 阿里云服务器、公网 HTTPS、个人账号登录。
- Vue 3 + Vite + Vue Router，Python Starlette 提供同源 /api/*。
- 上传单个 UTF-8 TXT 或 Markdown，手动处理后可检索正文。
- 资料详情、版本历史、上传新版本、改名、标签、移动目录。
- 文件夹创建、浏览、改名、移动、防环、整树回收与批次恢复。
- 资料筛选及混合正文检索，展示命中片段和资料来源。
- AI 问答留在后续阶段。原有 Agent/MCP 实现仍在项目中。
- 同名上传创建独立资料。详情页上传新版本才合并进原资料。
- 快照只存指针是用户有意采用的设计。
- 初版计划上传上限曾是 1 MiB，实际实现和 Vue 当前都采用 10 MiB。

## 功能进度

| 阶段 | 当前证据 |
|---|---|
| 01–02 Vue 入口与认证 | 本地验证通过，公网登录/会话/退出通过 |
| 03–07 浏览、上传、版本、整理、筛选分页 | 真实 PostgreSQL 和 Vue 组件逻辑验证通过 |
| 08 单份资料回收恢复 | 真实数据库验证原文、版本和原目录保留 |
| 09 文件夹移动 | 三轮并发相反移动，每轮恰好一个 204、一个 409 |
| 10–12 整树回收与恢复 | 迁移已生效，真实数据库验证批次隔离和并发写入 |
| 13 手动处理 | 真实 embedding API 验证发布切换、重复提交和失败状态 |
| 14 正文检索 | 真实 embedding + 混合召回 + rerank 验证回收/恢复及竞态过滤 |
| 15 部署 | 已上线，已修复数据库连接超时 |
| 16 公网端到端验收 | 尚需用新测试资料在浏览器完成完整业务流程 |

上表中的功能测试主要在 Windows 进程连接真实 PostgreSQL 时完成。不能把这些证据等同于服务器上传、索引、检索已经完整跑通。

## 代码入口

| 文件 | 职责 |
|---|---|
| config.py | .env、Settings、env_bool() 严格布尔解析 |
| db.py | auth_connection() 只读认证连接、user_transaction()、lock_folder_tree() |
| auth.py | authenticate_token()、authenticate_password()，Argon2 验证 |
| documents.py | upload_bytes()、资料/版本读取、改名标签移动、单份回收恢复 |
| folder.py | 目录操作、soft_delete_folder_tree()、list_deleted_folders()、restore_folder_tree() |
| processing.py | 默认处理配置、process_version()、运行查询、索引发布 |
| knowledge_service.py | search_knowledge()、fetch_knowledge() |
| retrieval.py / rerank.py | 混合召回与阿里云 rerank |
| web_app.py | Starlette create_app()、认证与业务 API |
| web_frontend.py | 生产 Vue 构建产物和已知页面路由 |
| frontend/src/views/ | LoginViews.vue、LibraryView.vue、DocumentView.vue、TrashView.vue、SearchView.vue |
| frontend/src/router/index.js | 登录守卫、页面路由 |
| init_sql/04_folder_trash.sql | 已部署的删除批次增量迁移 |

### 常用 HTTP 接口

- POST /api/auth/login，GET /api/auth/me，POST /api/auth/logout。
- GET/POST /api/documents。
- GET/PATCH/DELETE /api/documents/{document_id}。
- GET/POST /api/documents/{document_id}/versions。
- PUT /api/documents/{document_id}/tags 与 /folder。
- POST /api/documents/{document_id}/restore。
- GET /api/trash/documents 与 /api/trash/folders。
- GET/POST /api/folders，PATCH/DELETE /api/folders/{folder_id}。
- PUT /api/folders/{folder_id}/parent。
- POST /api/folders/{folder_id}/restore。
- POST /api/versions/{version_id}/process。
- GET /api/versions/{version_id}/processing-runs。
- POST /api/search。

web_app.py 还有 GET /api/folders/{scope}/{folder_id} 路由。当前 list_folders_endpoint() 读取 parent_id 查询参数，额外路径参数的语义应在实际使用前核实。

## 关键约定

### 登录与配置

- 用户名 strip().lower()。密码保留原始字符，明确禁止纯空白密码。
- SessionMiddleware 使用签名 Cookie，仅保存用户 UUID，HttpOnly、SameSite=Lax，有效期 8 小时。
- 生产 Secure=true，debug=false。退出清除当前浏览器 Cookie，复制出的旧 Cookie 仍可能有效到过期。
- 写接口检查 Origin，与 PERSONALRAG_WEB_ORIGIN 完全一致。
- env_bool() 只接受规范化后的 true/false。调试变量已修正为 PERSONALRAG_WEB_DEBUG。
- config.py 在导入时从代码旁的 .env 加载，override=True。修改环境变量或 .env 后重启服务。

### 目录与回收批次

- rag.folders 新增 deleted_at、trash_batch_id，必须同时为空或同时有值。
- rag.documents 新增 trash_batch_id。有批次时必须已删除，独立回收允许批次为空。
- 目录树写入共用事务锁 rag.folders-tree: + user_id，经 hashtextextended 转成 advisory lock key。
- 整树回收仅标记当前活跃子树和活跃资料，同一次操作共享批次 UUID 和删除时间。
- 先单独回收的资料或较早回收的子树保持原状态，恢复父目录不会把它们带回。
- 文件夹回收站每批只显示根目录，单份资料回收站排除有批次的资料。
- 按 user_id 和批次 ID 恢复，deleted_at、trash_batch_id 一起清空。
- 批次内子目录不能单独恢复。原父目录仍被回收时返回 409。
- 上传到目录、移动资料、目录创建/移动、单份资料恢复等路径已增加相同锁与目标活跃检查。
- 保留原父子关系、原文、版本和索引指针。同级名字在回收期间继续保留。

### 处理与检索

- process_version() 使用服务端默认配置，按版本和配置哈希复用运行。
- 同一失败运行重复提交不会自动重跑。Vue 已提示这个行为。
- POST process 当前返回空 200。Vue 兼容，并以 GET processing-runs 为状态来源。
- 只有成功处理最新上传版本时切换 active_run_id。上传 v2 或 v2 处理失败时，已发布 v1 继续可检索。
- is_latest_version 与 is_published 是不同状态。
- Vue 按页读取运行状态，每批最多 4 个并发查询，运行时轮询，离开页面停止定时器。
- 检索结果按召回和 rerank 排序，随后按 chunk_id 在 rag.searchable_chunks 再查元数据。
- 最后一次检查会丢弃搜索中途被回收或被替代的片段。
- 标签/标题筛选用参数化 SQL，标题转义 !、%、_，多标签用数组包含条件同时匹配。
- 列表按 updated_at DESC, id DESC 排序，offset 分页仅保证数据未变化时顺序稳定。
- Vue 列表每页显示 20 条，请求 21 条判断下一页。

## 当前部署

| 项目 | 值 |
|---|---|
| 操作系统 | Alibaba Cloud Linux 3.2104 U10，Linux x86_64 |
| Python | uv 安装的 CPython 3.11.18 |
| SSH | root，连接与认证信息见设备目录 |
| 项目目录 | /root/personalrag-v2/app |
| 原有 SQL 与数据目录 | /root/personalrag-v2 |
| Python 环境 | /root/personalrag-v2/app/.venv |
| 原文配置目录 | /root/personalrag-v2/data/raw |
| systemd 服务 | personalrag-v2-web.service |
| 本机 Web 地址 | http://127.0.0.1:8001 |
| 公网地址 | https://rag.191226269.xyz |
| 数据库 | personalrag_v2，业务和认证连接均使用 127.0.0.1:5432 |
| Tunnel | ali-personal-services，目标 http://127.0.0.1:8001 |

通过设备目录中的密码，Paramiko SSH 实际连接成功。原生 ssh 的当前环境缺少已知主机指纹，先前严格校验没有连上。后续使用 SSH 时重新核实连接方式，不要把先前密钥登录失败当成服务器不可访问。

生产 .env 必须包含以下开关，实际密钥继续在服务器原文件中保留：

    PERSONALRAG_WEB_ORIGIN=https://rag.191226269.xyz
    PERSONALRAG_WEB_DEBUG=false
    PERSONALRAG_WEB_COOKIE_SECURE=true
    PERSONALRAG_WEB_SERVE_FRONTEND=true
    PERSONALRAG_RAW_STORAGE_DIR=/root/personalrag-v2/data/raw

现有 load_settings() 仍要求读取模型配置与 MCP Token 等字段。当前网页不使用某些功能，也不能随意删除相应必填配置。

### 常用服务器命令

    cd /root/personalrag-v2/app
    systemctl status personalrag-v2-web --no-pager
    journalctl -u personalrag-v2-web -n 80 --no-pager
    systemctl restart personalrag-v2-web
    curl -sS http://127.0.0.1:8001/api/healthz

服务 ExecStart：

    /root/personalrag-v2/app/.venv/bin/python -m uvicorn web_app:create_app --factory --host 127.0.0.1 --port 8001

服务单元安装在 /etc/systemd/system/personalrag-v2-web.service。
上传包内的单元模板在 app/deploy/personalrag-v2-web.service，模板目前未单独保存到本地仓库。

### 本地上传包

路径：

    C:\Users\茶鸣拾贰率\.codex\visualizations\2026\11\05\01a1a9ce-32ef-7c40-8265-9057fa41d293\personalrag-v2-web-20261107.tar.gz

SHA256：

    7be5144656fed2abdf0be99802393deac158f7de8b3f59a2cfa95366db9a8565

包含 app/ 下的 Python 源码、uv.lock、前端源码和构建产物、.env.example、systemd 模板。
包内不含实际 .env、原始数据、.venv 或 node_modules。
这是发布时的固定快照，后续本地改动需要重新构建打包。
服务器 .env 已单独调整数据库主机地址，不应以本地开发 .env 覆盖。
本地和服务器的数据库地址应分别维护。

## 最近修复与证据

### DNS 与名称服务器切换

用户刚切换域名名称服务器时，新区域 pending。
当时公网 NS 仍返回 jermaine、maeve，新区域要求 katelyn、rodney。
rag CNAME 和 Tunnel ingress 已正确存在，但新区域尚未生效。
之后公网 A 记录出现，用户可以访问网页，公网页面也通过了 HTTP 测试。

当时先把问题归因于令牌权限不足的判断已被纠正。实际查到令牌包含该账号的 DNS/Zone/Tunnel 读写权限。不要要求用户再换令牌，也不要擅自把 NS 改回旧值。

当前执行环境的系统 DNS 曾返回 198.18.* 的代理地址，导致 TLS EOF。
公网验收改用公开 DoH 查询得到的地址建立连接，保持原 Host、SNI 与证书校验。

### 公网登录 500

服务器日志显示 psycopg.errors.ConnectionTimeout。
实际 SSH 检查确认 PostgreSQL 只监听 127.0.0.1:5432，但服务器两条 DSN 使用公网地址。
已先验证相同账号和密码连接本机地址成功，再只修正两条 DSN 的 host。
重启 Web 后在服务器本机验证登录、会话和资料列表成功。
随后通过公网 HTTPS 验证登录、Secure Cookie、会话、资料列表、文件夹列表和退出成功。
设备目录已更新，临时 SSH 依赖已清理。

## 测试与限制

已多次运行以下命令，最近一次检查结果为 49 tests OK：

    cd C:\PersonalRAG-v2
    .\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_*.py' -q

前端构建时使用 --configLoader native，并把产物输出到可写临时目录或上述 artifact 目录。
常规 Vite 配置加载曾因沙箱不能写 node_modules/.vite-temp 而报 EPERM。
此前本地 Node 为 24.11.1，frontend/package.json 声明 ^22.18.0 || >=24.12.0。正式复现构建时核对 Node 版本。

Vue 组件行为测试通过 compiler-sfc 编译真实组件，以自定义 renderer 和模拟 fetch 挂载，覆盖路由、编辑、上传、回收恢复、筛选、分页、处理轮询、搜索等。
这些测试以及大部分真实数据库流程测试由临时脚本执行，尚未作为回归测试全部落入仓库。
测试创建的 SQL 行、原文临时目录和临时服务均已清理。

真实浏览器视觉检查与完整操作验收尚未完成。
云端长期运行、重启恢复和大文件处理稳定性尚未验证。
历史资料原文是否全部同步至服务器的 raw 目录尚未验证。
原文路径保存的是指针，Windows 上有文件不代表服务器存在同一份原文。

## 建议接手后的第一件事

完成第 16 步，使用一份新建的小型测试资料，在公网浏览器依次验收：

1. 登录，创建两层目录，上传中文 TXT/Markdown，刷新后仍能浏览。
2. 上传新版本，检查最新上传和当前可检索标记，手动处理并检索预期片段。
3. 改名、标签、移动资料和文件夹，确认详情与列表一致。
4. 单份资料回收恢复，再测试先单独回收 A / 子目录 B、后回收父目录的批次隔离。
5. 退出后确认业务接口返回 401。
6. 经用户授权在维护窗口验证服务重启与已上传原文的可用性。

此后再做已出现问题的修复、必要回归测试与提交整理。AI 问答是后续阶段。

## 设备目录

    C:\Users\茶鸣拾贰率\Desktop\device.json

已增加 PersonalRAG v2 Web 服务与最近核验记录。服务器服务、端口或部署路径发生实际变化时，按用户规则增量更新，保留其他设备及历史信息。
