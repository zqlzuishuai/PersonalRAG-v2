# PersonalRAG：面向大模型应用实习的 LangChain 增强计划

> **范围更新（2026-11-10）：** 用户已明确优先快速学习 LangChain，只做后端。本文件保留为完整产品路线的历史参考；当前执行入口改为 [后端学习计划](2026-11-10-langchain-backend-learning.md)。下面的网页、生产持久化与完整评测任务不再是当前阶段的前置条件。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 PersonalRAG v2 中交付可演示的多轮知识库 Agent，并用可重复的评测说明检索与回答质量，支撑大模型应用 / Agent / RAG 实习面试。

**Architecture:** 复用现有检索、重排、用户隔离与文档版本体系，以 LangChain `create_agent` 承担工具调用循环，以 LangGraph 数据库检查点保存会话状态。Web 端通过服务器确认的用户身份调用工具，展示流式回答、执行状态和可核对来源；独立离线评测比较检索策略，LangSmith 作为可选追踪与实验后端。

**Tech Stack:** Python >=3.11、现有锁定版本的 LangChain / LangGraph、PostgreSQL / pgvector / BM25、psycopg、Starlette、Vue 3 / Vite / Naive UI；新增数据库检查点依赖在实施时按兼容性验证后锁定。

**状态：** 2026-11-10 编写，Asia/Hong_Kong。本文件为持久化方案，不代表业务代码已实现、测试已通过或服务已部署。用户尚未提供投递日期；以下以交付顺序安排范围，不承诺固定工期。

## Global Constraints

- 项目根目录为 `C:\PersonalRAG-v2`；`C:\PersonalRAG` 为另一套工作树，不交叉修改。
- 目标岗位已经确认：大模型应用 / Agent / RAG 开发实习。
- 本轮只编写计划，不修改业务代码、依赖、数据库、生产配置或设备目录。
- 现有工作树存在大量未提交改动；实施前记录基线，只提交本任务明确选择的变更，禁止 `git add .` 或覆盖用户改动。
- 不为技术名词重写现有向量检索、BM25、RRF、重排和文档管理逻辑。
- Web 用户身份只来自经过验证的服务端登录会话；模型参数、请求正文和 URL 中的用户 ID 均不是授权依据。
- 模拟测试、真实数据库验证、模型 API 验证和公网验收分别记录，不相互替代。
- 所有真实模型测试使用专用演示资料；不默认把个人知识库内容发送到新增的第三方追踪服务。
- 不预先声称准确率、召回提升比例、低延迟或成本下降；数字必须来自可复现的实际实验。

---

## 1. 为什么这样做

项目已经有检索、重排、MCP 和基础 Agent。当前最明显的缺口是：这些能力尚未形成网页上的完整问答体验，也缺少能说明效果与失败原因的实验材料。

本计划的主线是：**现有 RAG 基础 → 可用的知识库 Agent → 可核对的运行记录 → 有对照的效果评测。**

三个层次分别回答面试问题：

| 层次 | 用户得到什么 | 面试能解释什么 |
| --- | --- | --- |
| 产品闭环 | 多轮问答、流式输出、来源核对、刷新后查看历史 | 如何把模型与业务系统集成 |
| 工程可靠性 | 会话隔离、数据库持久化、失败状态、重复提交保护 | 如何处理权限、并发与故障 |
| 效果证据 | 检索对照实验、失败案例、耗时与用量记录 | 如何判断改进有效，而不是凭感觉调提示词 |

第一版不做多 Agent、自动写入长期用户画像、任意 SQL 工具、联网搜索和复杂人工审批。只有评测显示现有循环无法可靠处理某类问题，才引入显式 LangGraph 检索工作流。

### 技术边界澄清：LangChain 1.x 与 LangGraph

`create_agent` 本身基于 LangGraph 运行，使用它已经间接使用了 LangGraph。本计划 P0 不要求手写 `StateGraph`、节点、边或另一套 Agent 循环。数据库 checkpointer 直接传给 `create_agent`，流式输出使用返回 agent 的接口；上下文处理、工具限制和失败处理优先采用 LangChain middleware 及业务层校验。

选择顺序是：`create_agent` 配置 → middleware 扩展 → 必要时手写 LangGraph 编排。查询改写、补检索、会话持久化、流式响应或人工确认本身，都不单独构成手写图的理由；只有业务确实需要显式流程拓扑，且现有扩展方式难以清晰实现时，才考虑 P2。

## 2. 已检查的现状与未知项

以下来自本次本地代码检查，不是生产运行结论：

| 文件 | 已有能力 / 约束 | 实施含义 |
| --- | --- | --- |
| `agent_service.py` | `create_agent`、`MCPAdapter`、`InMemorySaver`、`ainvoke`、`thread_id`、递归上限 12 | 复用提示词与工具策略，新增 Web 可用的工厂和事件适配 |
| `auth_http.py`、`auth.py` | MCP Bearer Token 经数据库映射到所属用户 | 不能把配置中的单个 Token 当成所有 Web 用户的身份 |
| `retrieval.py` | 向量召回、BM25、RRF | 原检索函数保留，评测复用 |
| `knowledge_service.py` | 混合召回与重排、查询后再次核对可检索来源 | 新工具继续调用业务服务，保留回收和版本过滤 |
| `answering.py` | 聊天模型初始化、另一条回答路径、引用编号范围校验 | 编号合法不等于证据支持结论；不能当作语义质量保证 |
| `web_app.py`、`origin_guard.py` | Cookie 登录会话、来源校验、文档与检索接口 | 新写接口沿用相同边界；问答路由放独立模块 |
| `init_sql/01_schema.sql` | 已定义 conversations、messages、answer_runs、citations，含 RLS 与单会话 running 唯一索引 | 先核实实际数据库，优先复用，禁止重新运行整份建表脚本 |
| `frontend/src/App.vue`、`frontend/src/router/index.js` | 已有资料、检索和回收站导航 | 在现有布局增加问答入口，不重设计整个站点 |

尚未核实：真实库中这些表的当前结构与数据；本机已安装版本与锁文件是否一致；新增异步检查点依赖的兼容版本；模型的流式工具调用和 usage 返回行为；生产代理的流缓冲表现。均在相应任务验证，不写成既成事实。

## 3. 第一阶段：知识库 Agent 闭环（P0）

### 3.1 身份与工具接入

Web 内部优先直接包装 `search_knowledge(settings, user_id, query, top_k)` 和 `fetch_knowledge(settings, user_id, chunk_id)`，不让同进程服务为每次调用再经过 HTTP MCP，也不引入用户 Token 托管。

身份通过 LangChain Runtime Context 注入；模型可见的工具参数只包含问题、片段 ID 和数量。现有外部 MCP 服务继续支持外部客户端，使用相同业务函数。这是一套业务能力的两种接入方式，不声称 Web 内部也经过了 MCP。

拟新增的上下文与接口契约如下；它们是设计接口，实施时需对当前 SDK 写兼容性测试：

```python
@dataclass(frozen=True)
class AgentContext:
    user_id: UUID
    conversation_id: UUID
    run_id: UUID

def build_knowledge_tools(settings: Settings) -> list[BaseTool]: ...
def build_web_agent(settings: Settings, checkpointer): ...
async def stream_agent_turn(agent, context: AgentContext, query: str) -> AsyncIterator[ChatEvent]: ...
```

`Settings` 由工具工厂闭包持有，不把密钥放进模型消息或检查点。同步业务函数通过线程池调用。Web 请求先校验 conversation 的归属，再构造上下文；thread ID 由服务端生成 `user_id:conversation_id`，浏览器不能自行指定检查点 ID。

### 3.2 数据持久化与职责

- `rag.conversations`：会话归属、标题、消息序号与最近更新时间。
- `rag.messages`：用户可见消息的持久化记录，保存完整成功回答或标记过状态的中断草稿。
- `rag.answer_runs`：一次请求的状态、幂等请求 ID、检索与模型配置、用量、错误和执行时间。
- `rag.citations`：实际使用来源的片段 ID、版本、逐字摘录和定位；遵守现有触发器，不把摘要伪装成原文摘录。
- LangGraph PostgreSQL checkpointer：图执行状态与工具消息，用于多轮上下文，不代替以上业务表。

使用 SDK 提供的异步 PostgreSQL saver，生命周期由 Starlette lifespan 管理。检查点建表是显式迁移步骤，不在每个请求中 `setup()`。使用专门检查点连接配置，不给业务 app 角色增加整个数据库的 DDL 权限；具体包版本、表位置与所需权限在隔离库验证后写入迁移说明。

检查点库和业务表之间没有天然的跨连接原子提交。每轮以 `run_id` 关联：业务任务先持久化 running，图调用后将最终回答、引用与 succeeded 一次事务提交；出现检查点已经完成、业务事务未提交时，以 `run_id` 对账，不重复自动调用模型。无法确认完整性的轮次标记 failed，下一轮从成功消息构建干净上下文，不继续使用未完成工具消息。

同一会话通过现有数据库唯一索引保证只有一个 running 任务，冲突返回 409；不同会话可并行。`client_request_id` 相同且正文一致时返回已有任务，不重复计费；相同 ID 但正文不同返回 409。请求不保持跨模型调用的业务数据库事务。

第一版使用请求内执行、总时限 120 秒、工具调用总数上限 6，保留递归上限 12 作为另一道保护。断开连接即取消本轮，保存 cancelled 状态与未完成草稿；不实现断点续传和自动恢复生成。进程崩溃遗留任务按开始时间超过 150 秒后标记 failed，用户可发起新请求。未来多 worker 环境的回收按数据库条件原子更新，不能只扫描当前进程内存。

上下文首版仅保留最近 6 个成功轮次，输入问题最多 4000 字符，每次检索结果总正文最多 20000 字符；这些是可调预算，不宣称为模型通用最佳值。历史引用在再次传入模型前校验可见性；来源已回收或发布版本已变化时，移除相关旧工具证据及依赖它的回答上下文，要求本轮重新检索。页面历史保留并标记来源不可用，不能继续展示旧片段正文。该策略需覆盖检查点中的旧 ToolMessage，不可只过滤页面消息。

### 3.3 API 与流式事件

| 方法与路径 | 请求 / 响应 | 要求 |
| --- | --- | --- |
| `POST /api/conversations` | `{title?: string}` → `{id, title}` | 已登录，同源，标题最多 100 字符 |
| `GET /api/conversations?limit=20&offset=0` | `{conversations: [...]}` | 只返回当前用户；limit 范围 1–100 |
| `GET /api/conversations/{id}/messages?limit=50&before_sequence=...` | `{messages: [...], has_more: bool}` | 只返回所属用户的历史及可见引用 |
| `POST /api/conversations/{id}/turns` | `{query, client_request_id}` → SSE 事件流 | 身份、归属、来源、预算和任务占用检查在响应开始前完成 |
| `GET /api/conversations/{id}/runs/{run_id}` | `{status, answer_message_id, error_code}` | 重复提交和断开后核对结果，不触发生成 |
| `GET /api/chat/sources/{chunk_id}` | `{document_id, version_id, title, content, locator}` | 复用可见性校验，不直接按 UUID 绕过用户和版本过滤 |

无登录返回 401，其他用户会话与不可见来源统一 404，外部来源请求 403，参数错误 400，任务冲突 409，流前依赖不可用 503。流开始后出错用 `error` 事件表达，不假装还能修改 HTTP 状态码。

浏览器用 `fetch` 的 POST 响应流解析 SSE，不使用只支持 GET 的原生 EventSource 提交问题。事件含 `event_id`、`run_id` 和类型专属字段：

```json
{"type":"run_started","run_id":"uuid","event_id":1}
{"type":"tool_started","run_id":"uuid","event_id":2,"tool":"rag_search"}
{"type":"tool_finished","run_id":"uuid","event_id":3,"tool":"rag_search","result_count":5}
{"type":"answer_delta","run_id":"uuid","event_id":4,"text":"根据资料，"}
{"type":"sources","run_id":"uuid","event_id":5,"sources":[{"citation_no":1,"chunk_id":"uuid","document_id":"uuid","version_id":"uuid","quote":"逐字原文"}]}
{"type":"done","run_id":"uuid","event_id":6,"answer_message_id":"uuid"}
```

`done` 与 `error` 互斥且至多一次；`done` 仅在业务结果成功提交后发送。每 15 秒可发 SSE 注释心跳；响应采用 `text/event-stream`、`Cache-Control: no-cache`，并验证实际代理链没有缓冲。流只投影工具状态和助手可见正文，不展示工具参数碎片、凭据、原始协议消息或模型内部推理。模型在工具调用前输出的文字不作为“已验证最终答案”；最终消息持久化时只采集本轮最终回答，避免把中间助手消息拼进最终答案。

引用采用服务端证据注册表：工具返回的片段获得本轮编号；模型使用 `[n]` 引用。结束时核对编号来自真实工具结果、摘录确为子串、来源仍可见。结果结构合法不等于结论被支持，语义支持率进入第二阶段评测。引用失效则保留回答草稿并返回错误，不发成功事件。无证据回答可以不含引用，但必须说明资料不足；寒暄可直接回答。

### 3.4 页面交付

新增 `/chat`，复用现有布局、登录路由守卫与 Naive UI。包含会话列表、消息区、输入框、停止按钮、简明工具状态、来源卡片和来源抽屉。来源卡片可查看本轮确实获得的摘录与版本，也可跳转 `/documents/{document_id}`；不声称现有文档页已经支持全文高亮。

输入提交后立即展示用户问题与等待状态；流中逐步更新回答，成功后可刷新重看。取消、失败和未完成草稿有明确标记；不自动重试 POST。Markdown 使用安全渲染，禁止任意 HTML；如增加 Markdown 依赖，应锁定并测试脚本链接和 HTML 注入。手机端来源抽屉与输入区域不遮挡主要内容。

## 4. 第一阶段执行任务

各任务按顺序实施，先写针对真实风险的行为测试，再实现最小改动。以下命令均从 `C:\PersonalRAG-v2` 执行；命令是未来验证要求，并未在计划编写阶段运行。

### Task 1：建立兼容性与权限基线

**Files:** 检查 `pyproject.toml`、`uv.lock`、`config.py`、`agent_service.py`、`init_sql/01_schema.sql`；新增 `tests/test_agent_sdk_contract.py`、`docs/validation/langchain-agent-baseline.md`。

- [ ] 记录工作树改动及依赖版本，核对 SDK 的 runtime context、工具调用、异步事件接口和 saver 生命周期；不先执行全量依赖升级。
- [ ] 用伪模型与伪工具写 SDK 契约测试：模型看不到 user_id；工具读取到服务端上下文；可区分工具事件与助手文本。
- [ ] 在隔离测试库核对会话相关表、RLS、引用触发器和 single-running 索引，记录与源码差异；不连接生产库执行初始化。
- [ ] 锁定一种实际可用的流 API。优先验证当前官方推荐的 event streaming；若本地 SDK 不兼容，则使用已经验证的 `astream` 并包在统一适配层，页面协议不依赖 SDK 事件形状。
- [ ] 运行 `.\.venv\Scripts\python.exe -m unittest tests.test_agent_sdk_contract -v`；验收是契约断言通过，并有明确依赖与数据库前置清单。

### Task 2：实现身份绑定工具和会话存储

**Files:** 新增 `agent_tools.py`、`chat_store.py`、`tests/test_agent_tools.py`、`tests/test_chat_store.py`；必要时新增 `init_sql/06_chat_runtime.sql`（只做经核实缺少的增量结构）。

**Interfaces:** `AgentContext` 与 `build_knowledge_tools` 采用 3.1 契约；`create_conversation(settings, user_id, title)`、`list_conversations(settings, user_id, limit, offset)`、`get_conversation(settings, user_id, conversation_id)`、`start_turn(settings, user_id, conversation_id, query, client_request_id)`、`finish_turn(settings, user_id, run_id, answer, citations, usage)`、`fail_turn(settings, user_id, run_id, status, error_code, partial_text)` 为业务存储接口。返回 DTO 使用显式 dataclass，不把数据库连接暴露给页面。

- [ ] 先写行为测试：A 不能读取 B 的会话；模型构造 user_id 参数不能改变工具身份；工具必须经过现有知识服务。
- [ ] 实现用户事务内的会话 CRUD、序号分配和任务占用；重试同一请求不新增消息，正文不一致报冲突。
- [ ] 按既有触发器顺序创建用户消息和回答占位；成功事务先完成 assistant message，再更新 answer_run 为 succeeded。
- [ ] 在真实隔离库使用 app 角色验证跨用户 RLS、双并发 409、提交失败回滚、原文摘录约束；模拟测试不能替代此步。
- [ ] 运行 `.\.venv\Scripts\python.exe -m unittest tests.test_agent_tools tests.test_chat_store -v`；验收是授权、幂等、序号和终态契约均通过。

### Task 3：接入数据库检查点和受控 Agent 执行

**Files:** 修改 `agent_service.py`、`config.py`、`pyproject.toml`、`uv.lock`；新增 `chat_runtime.py`、`chat_sources.py`、`tests/test_chat_runtime.py`、`tests/test_chat_sources.py`、`init_sql/07_chat_checkpoints.md`。

**Interfaces:** `chat_sources.py` 提供 `SourceRegistry` 管理本轮编号、引用验证和来源可见性；`chat_runtime.py` 提供异步生命周期 `chat_runtime(settings)` 以及 `stream_agent_turn`；新增配置 `PERSONALRAG_CHECKPOINT_DATABASE_URL` 仅服务端读取，repr 和日志不得输出。

- [ ] 先写同会话记忆、跨会话隔离、工具上限、120 秒超时、取消、模型异常和非法引用测试。
- [ ] 增加独立的 Web Agent 工厂；现有 MCP CLI 路径保留，用相同业务能力，不偷偷改变 CLI 身份语义。
- [ ] 在独立库运行 saver setup、权限检查和重启后继续成功会话测试；记录准确命令、表与角色权限。
- [ ] 实现运行记录对账及失败轮次清理；注入“图成功但业务提交失败”“消息提交成功但网络断开”验证不会误报成功或重复生成。
- [ ] 加入历史预算及证据可见性过滤；删除 / 回收 / 发布新版本后，旧工具正文不再自动进入下一轮模型上下文。
- [ ] 运行 `.\.venv\Scripts\python.exe -m unittest tests.test_chat_runtime tests.test_chat_sources -v`；另用真实隔离库完成重启验收，报告区分两种证据。

### Task 4：提供问答接口与稳定事件协议

**Files:** 新增 `chat_api.py`、`chat_events.py`、`tests/test_chat_api.py`、`tests/test_chat_events.py`；修改 `web_app.py`。

**Interfaces:** `chat_routes()` 返回 3.3 中的 Starlette routes；`ChatEvent` 定义事件类型和 JSON 数据；事件编码器输出 `event: <type>\ndata: <json>\n\n`。SDK 事件仅由服务端适配器消费。

- [ ] 先测试 401 / 403 / 404 / 409 / 503、问题长度、UUID 格式，以及响应开始前不调用模型的拒绝路径。
- [ ] 接入 lifespan，注册独立路由，保持已有资料 API 行为；新增 body 上限 32 KiB。
- [ ] 测试 SSE 有序事件、心跳、工具失败、最终提交失败、浏览器断连和终态互斥；usage 缺失写 null，不填 0 冒充统计。
- [ ] 测试重复提交仅查询已有 run 状态，不开启第二次模型调用；150 秒过期任务回收使用数据库条件更新。
- [ ] 运行 `.\.venv\Scripts\python.exe -m unittest tests.test_chat_api tests.test_chat_events tests.test_origin_guard tests.test_web_frontend -v`；验收为新协议与既有会话、来源校验回归通过。

### Task 5：接通网页问答和来源查看

**Files:** 新增 `frontend/src/views/ChatView.vue`、`frontend/src/components/ChatMessage.vue`、`frontend/src/components/ChatSources.vue`、`frontend/src/data/chatStream.js`、`frontend/tests/chat-stream.test.mjs`；修改 `frontend/src/App.vue`、`frontend/src/router/index.js`。

**Interfaces:** `readChatStream(response, {onEvent, signal})` 负责 SSE 分帧解析，页面按 run_id 更新当前轮；来源卡片只消费结构化 sources，不从文本中猜 document_id。

- [ ] 先给解析器写 node:test：UTF-8 跨字节拆包、跨网络块事件、多行 data、心跳、异常结束与非法 JSON。
- [ ] 实现会话列表、提交、流式更新、取消、失败反馈、刷新历史；切换会话时停止旧请求并忽略旧 run 事件。
- [ ] 实现来源抽屉与文档跳转；404 显示“来源当前不可用”，不得展示浏览器缓存的旧正文；回答内容按安全 Markdown 或纯文本渲染。
- [ ] 运行 `npm --prefix frontend test` 和 `npm --prefix frontend run build`，确认退出码为 0；实际浏览器检查桌面与 390px 窄屏、键盘操作、自动滚动和无控制台错误。
- [ ] 用两名测试用户完成多轮、刷新、取消、资料回收与越权访问验收；测试数据记录在专用演示目录，验收结束清理临时账号与资料。

## 5. 第二阶段：评测与可观测性（P1，独立交付）

前置条件是 P0 能运行。P1 不阻止问答闭环单独验收；如果时间有限，先交付 P0 和一份本地评测报告，再扩展云端实验展示。

### Task 6：构建固定评测集和检索对照

**Files:** 新增 `evals/README.md`、`evals/datasets/demo-rag-v1.jsonl`、`evals/fixtures/`、`evals/run_retrieval.py`、`evals/run_agent.py`、`evals/metrics.py`、`tests/test_eval_metrics.py`、`docs/validation/langchain-evaluation.md`。

- [ ] 编写 40 条人工核对样例：精确 / 语义检索 12、需拆解的跨文档问题 8、多轮指代 8、资料不足 8、冲突资料及文档内指令干扰 4；这只是初始功能覆盖集，不代表通用基准。
- [ ] 每条记录包含 `id`、`category`、`turns`、`answerable`、`reference_facts`、`relevant_sources` 与 `split`。来源采用演示资料逻辑键和稳定定位映射，不硬编码一次导入生成的随机 UUID。
- [ ] 固定 30 条开发样例、10 条保留样例；多轮整组与同类问题变体放在同一 split。报告小样本分母与局限，不把保留集反复当提示词调参集。
- [ ] 对比三组：向量召回；混合召回 + RRF；混合召回 + RRF + 重排。固定资料版本、切分、embedding、最终 top_k=5；混合组固定 candidate_k=30，向量组记录对应候选预算。分别记录检索耗时和重排耗时。
- [ ] 检索指标报告 Hit@5、Recall@5 和 MRR@5；无标注来源的问题不参与召回指标。多跳问题用所需来源集合计算 Recall，不能只命中一段就认定整题成功。
- [ ] Agent 指标包括事实正确性、引用支持性、资料不足时的适当拒答、工具成功率、完整请求耗时、首个回答文本耗时和模型 token 用量。结构化指标用代码，语义指标人工抽检；可选 LLM judge 标明模型与评分标准，不作为唯一真值。
- [ ] 输出带数据集 hash、Git 提交及脏工作树标记、模型 / 提示词版本、资料版本、参数、时间与样本数的 JSON 和 Markdown；不覆盖上次实验。
- [ ] 用 `.\.venv\Scripts\python.exe -m unittest tests.test_eval_metrics -v` 验证已知排序样例；用 `.\.venv\Scripts\python.exe -m evals.run_retrieval --dataset evals/datasets/demo-rag-v1.jsonl --split all --output artifacts/evals/retrieval-v1` 执行专用测试库检索实验。
- [ ] 用 `.\.venv\Scripts\python.exe -m evals.run_agent --dataset evals/datasets/demo-rag-v1.jsonl --split holdout --output artifacts/evals/agent-v1` 运行真实模型实验；命令需由本任务实现，输出报告包含成功数、失败数和未执行项，不在编写计划时宣称已有结果。

### Task 7：追踪、成本记录和展示材料

**Files:** 新增 `observability.py`、`tests/test_observability.py`、`docs/interview/demo-script.md`、`docs/interview/design-decisions.md`；修改 `config.py`、`chat_runtime.py`、`README.md`。

- [ ] 本地先记录 run_id、工具名、耗时、错误类别与 provider 返回的 usage；凭据、Cookie 和个人正文不入普通日志。token 缺失不凭字符数补造。
- [ ] LangSmith 默认关闭；显式开启演示模式时仅使用合成 / 公开演示资料，建立与 run_id 关联的 trace。平台中断不影响主问答功能，增加失败降级测试。
- [ ] 如报告费用，保存价格来源、计价日期、缓存 token 规则和计算方式；仅有 token 统计时称“用量”，不称真实账单。
- [ ] 生成 5 分钟演示脚本：上传并处理演示资料 → 提问 → 多轮追问 → 查来源 → 资料不足示例 → 查看追踪 → 比较评测结果。重启恢复在本地测试服务演示，不临时重启生产。
- [ ] 写清至少五个设计取舍：Agent 与固定链、MCP 与进程内工具、checkpointer 与业务消息、RRF 与重排、流式响应与失败终态。
- [ ] 简历只描述实际交付的范围；量化项从报告填写，未测得改善就展示真实结果与失败分析，不预填提升比例。
- [ ] 运行 `.\.venv\Scripts\python.exe -m unittest tests.test_observability -v`；验收为追踪开关和失败降级有效，并有可重复的演示和实验材料。

## 6. 第三阶段：确有复杂编排需求时手写 LangGraph 工作流（P2）

此阶段不在默认首版范围，也不要求最终必须实施。先用评测定位问题，依次尝试工具描述、检索参数、提示词与 middleware。即便存在查询表达不足、多跳证据遗漏或重复无效检索，也不能直接推出需要手写图。

只有确实出现需要显式建模的流程，例如多个受控检索分支并行后统一汇合、各阶段有不同状态与重试规则、确定性步骤与多个 Agent 交错执行，且用现有 Agent 循环和 middleware 实现已难以清晰维护时，才为手写图单独立项。

届时另写实施计划：`问题解析 → 必要时改写 → 检索 → 证据检查 → 回答或拒答`，证据不足最多补检索一次。显式状态包括原问题、改写问题、来源集合、检索轮次和停止原因。拿同一保留集对比现有 `create_agent` 基线，同时报告质量、延迟和调用成本；收益不足则保留简单基线。

不把“模型又检查了一次自己的答案”当成可靠性证明，也不把一次来源不命中解读为知识库中必定没有答案。

## 7. 验收与交付顺序

1. **P0 后端验收：** 用户隔离、幂等、串行执行、工具预算、真实库重启记忆、引用约束与失败对账通过。
2. **P0 产品验收：** 登录后完成连续问答、停止、刷新历史、来源查看；已有上传 / 检索 / 文档页面回归通过。
3. **P1 证据验收：** 40 条标注样例、三组检索实验、保留集 Agent 结果、明确失败案例和可复现报告齐全。
4. **展示验收：** 可以用 5 分钟展示功能，再用 5 分钟解释两项设计取舍和一次失败分析。
5. **生产上线：** 独立任务。先核对设备目录和真实服务状态，再准备迁移备份、回滚、测试账号清理及分阶段发布；本计划不执行上线。

未通过 P0 时不写“完整 Agent 已交付”；只有模拟测试时不写“数据库隔离已验证”；没有实验结果时不写“准确率提升”。

## 8. 实施时的提交与清理

- 每个任务通过自身检查后选择性提交该任务文件；共享文件中混有用户改动时先确认 diff，不能一并打包。
- 文档路径均相对 `C:\PersonalRAG-v2`；本计划本身不自动提交，以免混入现有暂存改动。
- 真实 API 测试前列明会产生调用用量；只在专用测试资料中操作。
- 清理本次临时账号、资料、隔离库与容器，保留必要评测样例、正式报告和审计证据；不删除未知资源。
- 设备或持久服务配置确实变更后，按项目全局规范增量更新 `C:\Users\茶鸣拾贰率\Desktop\device.json`，不输出凭据。

## 9. 官方参考与验证边界

2026-11-10 阅读的官方文档：

- [LangChain Runtime：用户身份与依赖注入](https://docs.langchain.com/oss/python/langchain/runtime)
- [LangChain Middleware：扩展 Agent 与嵌入自定义图的边界](https://docs.langchain.com/oss/python/langchain/middleware/overview)
- [LangChain Streaming：事件与流式输出](https://docs.langchain.com/oss/python/langchain/streaming)
- [LangGraph Persistence：checkpointer 与 store](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Memory：数据库持久化](https://docs.langchain.com/oss/python/langgraph/add-memory)
- [LangSmith Evaluation：数据集与实验](https://docs.langchain.com/langsmith/evaluation)
- [LangSmith Tracing：追踪接入](https://docs.langchain.com/langsmith/observability-quickstart)

文档描述产品能力，不证明本地已安装 SDK、模型供应商或生产代理支持相同接口。执行 Task 1 的契约检查后才能确定具体调用方式。

## 10. 计划自检记录

- 已将用户目标映射为产品、可靠性、效果和面试材料四类交付。
- 已区分现有代码、拟新增接口、隔离环境验收和生产未验证项。
- 已拆出 P0 与可独立交付的 P1，P2 仅按评测证据触发。
- 已复用原有会话表，明确 MCP 身份与 Web 身份不能混用。
- 已写明检查点与业务表不天然原子、失败不能误报成功、历史工具证据需要重新过滤。
- 所有任务保持未勾选，待实际执行后记录结果。
