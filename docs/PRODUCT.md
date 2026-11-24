# PersonalRAG 产品范围、流程与交付

> 接续状态：2026-11-18（Asia/Hong_Kong）。**先交付产品，再继续单独的 LangChain/Agent 学习。** 当前接续点：**W1 · 验证已有持久化问答服务，接通第一条受认证的 Web 问答链路。**

**目标：** 用户能把网页当作文件仓库，在浏览器上传、查看、编辑文件原文并查看版本；也能处理和检索资料、获得可核对来源的回答，并用 MCP 客户端查询同一份已发布资料。

**架构决策：** 保留现有 Vue 3 和 Starlette 网页。在网页中使用固定 RAG，由 Web 会话确定用户后直接调用已有 Python 服务；MCP 保持独立的 Streamable HTTP 入口，用个人 Bearer 凭据查找用户，复用同一份资料与业务函数。网页不经 MCP 转发，不需要先接 Agent。直接上 Agent 能支持按需补查，但会同时引入工具调度、流事件和来源收集的验收负担；放在产品主链路完成后单独验证。

**复用：** `documents.py`、`processing.py`、`knowledge_service.py`、`answering.py`、`conversations.py`、`chat_service.py`、`answer_runs.py`。保留现有数据库与前端，不替换检索、不重写资料页。

## 当前证据

| 项目 | 已知状态 | 验证边界 |
| --- | --- | --- |
| 新文档到固定 RAG 回答 | [正常样例](validation/stage1-rag-sample-20261118.json)和[证据不足样例](validation/stage2-insufficient-evidence-20261118.json)均有通过记录 | 来自先前的真实后端运行记录；不代表 Web、MCP 或持久化问答服务已经通过。 |
| 网页 | 本地有登录、上传、处理、资料版本、正文检索等路由和 Vue 页面；`/api/search` 返回命中片段。缺少按版本读取完整原文和在线编辑正文的入口，也没有接入 AI 问答的 Web 路由或 Vue 页面 | 本轮静态核对。[既有部署交接](../HANDOFF.md)有历史记录，本轮未探测公网运行状态。 |
| 固定问答服务 | `chat_service.ask_question` 有创建/复用运行、生成回答、保存消息及引用的逻辑；`get_answer_run_result` 能按用户读取结果 | 本轮静态核对。`generate_system_message` 当前只使用本次问题及检索资料；保存聊天历史并不代表模型会读历史。 |
| MCP | `mcp_server.py` 有 `rag_search`、`rag_fetch` 和 Bearer 鉴权；`mcp_client.py` 有列出工具、搜索和按片段 ID 读取的示例 | 本轮静态核对。目标客户端远程接入、缺失或无效凭据、跨用户访问、凭据轮换均未在本轮实测。 |
| 已记录的回归 | `test_answering_citations.py` 6 项通过；`test_processing.py` 12 项通过 | 单元测试证据：包含引用编号范围、处理失败不发布部分结果等用例；不是 Web/MCP 或真实故障验证。 |

## 第一版产品范围

- **网页也是文件仓库。** 首版支持上传 UTF-8 TXT / Markdown，在资料详情打开最新及历史版本的完整原文，在线编辑最新版本并保存、回看历史；已有目录、改名、标签、回收和恢复流程保留。正文检索片段、文件元数据编辑和重新上传文件都不能替代网页原文查看与编辑。
- **保存与发布分开。** 正文有变化时保存为同一资料的新版本，保留旧原文；网页立即能打开新版本，并说明它尚未发布。沿用手动处理流程，处理成功后网页问答、正文检索和 MCP 才切换到新版本；未处理或处理失败时继续使用旧的已发布版本。
- 问答可展示引用对应的资料和版本、原文摘录。一条无依据的答案不显示为有来源的成功回答；检查时区分「引用能定位原文」与「原文支持结论」。
- MCP 先提供只读的 `rag_search` / `rag_fetch`。先用现有客户端脚本做协议烟雾测试，再用实际目标 MCP 客户端验收。支持该客户端配置的 HTTPS 与个人 Bearer 方式；如果目标客户端仅支持标准 OAuth，先记录兼容性差异，再单独规划授权接入。
- 两端的身份均由服务端认证得出；不信任请求体传入的用户 ID。使用真实测试账号 A、B 验证搜索、引用和原文访问权限。
- PDF / Office 等格式的在线查看与编辑、富文本协同编辑、写入型 MCP 工具、模型跨轮读取历史、流式回答、持久化 Agent 和八题评测不阻塞第一版。网页先返回完整回答；可以回看会话，首版问答按当前问题独立检索。

## 如何运行与验证现有功能

1. 使用隔离的 PostgreSQL 与测试账号；先看[数据库初始化](../init_sql/README.md)、[BM25 配置](../init_sql/BM25.md)及[项目 README](../README.md)。用项目锁文件安装 Python 依赖（在根目录执行 `uv sync --locked`），在仓库配置 `.env` 中填入 `config.py` 和 `web_app.py` 要求的数据库、原文目录、模型和会话配置；不要把生产配置直接复制进测试环境。
2. 从根目录运行 `.\.venv\Scripts\python.exe -m uvicorn web_app:create_app --factory --host 127.0.0.1 --port 8001`，通过 `/api/healthz` 确认服务启动，再按[前端指南](FRONTEND.md)启动 Vue；本地 `PERSONALRAG_WEB_ORIGIN` 要和实际访问前端的 origin 一致。现有网页可登录 → 上传 TXT / Markdown → 在版本详情点击「处理」 → 等待已发布 → 到「正文检索」查询已发布片段。速览当前只显示资料及版本信息。
3. 在同一隔离环境另开终端启动 `.\.venv\Scripts\python.exe mcp_server.py`；监听配置使用 `PERSONALRAG_MCP_HOST`、`PERSONALRAG_MCP_PORT`，本地绑定回环接口且不占 Web 端口。用分配给测试账号的个人凭据调用 `mcp_client.test_mcp(url, token, query)` 或实际客户端，对 `/mcp` 进行初始化、列工具、`rag_search`、`rag_fetch`。核对版本和片段是否与网页搜索一致。角色、凭据边界与 RAG 入口见[后端指南](RAG-AGENT.md)。

## W1 · 接通 Web 问答 API

- [ ] 用隔离测试环境，调用 `conversations.create_conversation(settings, user_id, title)` → `chat_service.ask_question(settings, user_id, conversation_id, query, client_request_id, chat_model)`，再用 `get_answer_run_result` 读取持久化答案。以现有的公开测试事实核对答案、引用编号、文档版本和片段。若持久化失败，先定位并修复这个环节。
- [ ] 在 `web_app.py` 接入最小的经过认证的创建会话和提问接口。建议 `POST /api/conversations` 接收 `title`，返回 `201` 和 `conversation_id`；`POST /api/conversations/{conversation_id}/answers` 接收 `query` 与 `client_request_id`，返回 `run_id`、状态、回答和引用。沿用现有 Web session、来源校验及 thread pool；接口只负责校验、身份、序列化和错误映射，服务层保留读写与模型调用。
- [ ] 用 `tests/test_web_chat.py` 验证通过与拒绝两条链：有效会话返回可用 JSON 和引用；未登录 `401`，不允许的请求来源 `403`，非法输入 `400`，不存在或不属于自己的会话/结果 `404`，重复请求编号绑定到不同请求、同一会话已有请求在运行时返回冲突。相同请求重试要读已有结果，不再调用模型。对外错误不暴露异常内部细节。
- [ ] 补充会话列表、消息历史与单次运行读取接口，用于 W2 刷新恢复。只返回当前用户的数据；正常生成、处理中、失败、可重试要可区分。对超时或进程中断留下的 `running` 记录至少有可操作的排查和恢复说明；避免盲目用新 UUID 重发。

**首个小步：** 只做 W1 第一条，确认真实持久化结果，再决定第一处代码改动。实现 API 后，定向运行 `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_web_chat.py' -v`。

## F1 · 网页文件仓库：查看与编辑原文

F1 与 W1 可以独立开展；它们都是网页端到端验收的前置项。复用现有资料详情、版本历史和处理入口，不另建一套存储或索引。

- [ ] 在 `documents.py` 增加指定版本的原文读取服务，在 `web_app.py` 暴露受认证的 `GET /api/documents/{document_id}/versions/{version_id}/content`。按当前会话租户核对资料归属、非回收状态及版本是否确实属于该资料，再用现有 `storage_path` 边界读取并核对原文完整性；返回文本、版本号和类型，不返回磁盘路径。缺失或损坏的原文要有明确错误，不能以空文档代替。
- [ ] 在 `web_app.py` 增加 `POST /api/documents/{document_id}/edits`，接收 `base_version_id` 和 `content`。服务层在 `upload_bytes` 写入事务已有的资料行锁内核对基准版本是否仍是最新；过期返回 `409` 并保留界面中的未保存文本。复用 UTF-8、大小限制与版本快照规则；内容未改变不创建新版本；内容改变只更新最新原文版本，不改变已发布的处理运行。沿用会话、来源校验和同一套用户权限。
- [ ] 在 `frontend/src/views/DocumentView.vue` 让每个版本可打开完整原文，最新版本可用文本编辑器保存，历史版本只读。内容作为文本呈现；保留未保存提示、保存失败反馈，明确区分「最新原文」与「已发布用于检索」。
- [ ] 文件仓库验收：账号 A 在浏览器打开文件第 1 版、更改正文并保存为文件第 2 版，确认第 1 版原文未变；用两个标签页模拟旧版本编辑冲突；账号 B 直接访问两个文件版本的原文及保存接口都不能读写。验证保存第 2 版后仍检索第 1 版，第 2 版处理成功后才切换；另用失败的新版本验证不改变已发布版本。

## W2 · 让网页能独立完成 RAG 工作流

- [ ] 在 `frontend/src/views/ChatView.vue`、`frontend/src/router/index.js`、`frontend/src/App.vue` 接入受登录保护的「知识库问答」；沿用现有布局和界面组件。支持提问、加载、可读的失败/无证据反馈、引用展开、历史恢复和同请求的重试。
- [ ] 引用展示编号、来源文档、版本与原文摘录；可用来源打开 F1 的对应版本原文。已删除或不可访问的来源清楚显示状态并且不能继续读取。不能把旧版本的引用静默跳转为当前版本。
- [ ] 构建命令：在仓库根目录运行 `npm --prefix frontend run build`。用浏览器和隔离测试账号完成：登录 → 上传未导入的 Markdown → 处理 → 正文检索 → 提问 → 核对引用和原文 → 刷新恢复历史。加查证据不足与会话失效；用失败的新版本核对未误发布，且旧的已发布版本仍可检索。

## M1 · 让同一知识库通过 MCP 可用

- [ ] 保留 `mcp_server.py` 的工具接口及 `knowledge_service.py` 数据边界。用现有 `mcp_client.py` 或等价客户端对隔离实例做真实 HTTP 握手、列工具、搜索并读取 W2 文档；以 `document_id`、`version_id`、`chunk_id` 和原文确认两端读的是同一已发布内容。
- [ ] 核对身份、工具返回与传输错误：无凭据/无效凭据返回 `401`；账号 B 搜不到测试账号 A 的独占事实，且持有 A 的片段 ID 也不能读取；无效 `top_k`、无结果及上游失败均可区分。核对允许来源、回环监听与反代 HTTPS 设置。只记录验证结果，不记录原始 Token。
- [ ] 补齐个人凭据的签发、轮换与撤销路径和 README：先复用每用户一个 `mcp_token_hash` 的存储方式；管理员流程可先用于验收，自助管理界面不会阻塞首轮。轮换或撤销后旧 Token 失效；原始 Token 仅在签发时交付并由客户端安全保存，不出现在日志、网页存储或工具响应。
- [ ] 用实际客户端验收同样流程，并记录支持的传输方式、配置方式和限制。协议参考：[MCP Streamable HTTP](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)。

## R1 · 两端联调与发布验收

- [ ] 在同一隔离环境完成一条联合场景：浏览器上传并发布文件第 1 版 → 在网页查看、修改原文并保存为文件第 2 版 → 第 2 版未发布时 Web 与 MCP 仍读第 1 版 → 处理并发布第 2 版后两端均读取新版 → 网页仍可打开第 1 版历史原文，旧回答引用仍指向原版本。账号 B 通过 Web 和 MCP 均无法访问该资料；处理失败、凭据失效、后端异常能在各端得到可理解的结果。
- [ ] 记录实际版本、环境、测试账号范围、代码入口、用例及结果。应用回归运行 `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v`，单独保存前端构建和实际客户端证据。
- [ ] 准备测试环境安装、健康检查、生产发布及回退说明，参考[部署交接](../HANDOFF.md)。先完成可审查的发布候选，实际部署及公网写入验收单独确认；本计划不能视为已经部署授权或已经公网验证。公网发布时复测实际用于交付的 Web 与 MCP 入口。

## 接续约定

- 本文是产品交付主计划。[RAG 后端与 LangChain Agent](RAG-AGENT.md)保留既有证据及学习任务；等产品主线验收后恢复 Agent 对照和面试稿。
- 每完成一项才勾选，记录日期、环境、验证方式、实际结果和第一个未通过的环节。区分静态检查、单测、真实后端、浏览器及真实 MCP 客户端、已发布的公网证据。
- 本项目根目录是 `C:\PersonalRAG-v2`。文中的「第 1 版」「第 2 版」是同一文件的历史版本，不是两个项目目录。
