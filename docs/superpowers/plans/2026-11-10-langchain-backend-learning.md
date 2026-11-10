# PersonalRAG：LangChain 后端学习实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过 PersonalRAG 的后端代码快速掌握 LangChain 1.x 的模型、消息、工具、Agent、会话记忆、流式输出和 middleware，最终用终端演示知识库问答。

**Architecture:** 先用最小脚本理解模型与工具，再阅读并复用 `agent_service.py` 中的 `create_agent` 与 MCP 工具链，在终端完成多轮问答和流式事件展示。已有知识库检索、数据库隔离和模型配置继续复用；不新增前端，不手写 LangGraph 状态图。

**Tech Stack:** 当前项目锁定版本的 Python / LangChain / LangGraph / MCP，现有模型供应商与知识库服务；终端使用现有 rich 或普通 print。

**状态：** 2026-11-10，Asia/Hong_Kong。仅计划已落盘，学习脚本和新增功能尚未实施。本计划替代原产品路线作为当前执行顺序；此前 Web 交付要求不适用于当前阶段。

## Global Constraints

- 根目录为 `C:\PersonalRAG-v2`，不修改 `C:\PersonalRAG`。
- 用户明确要求只做后端，以快速学习 LangChain 为优先目标。
- 不新增或修改前端页面、组件、样式与构建流程，不部署生产服务。
- 不把 API 服务、数据库检查点、完整评测平台或 LangSmith 注册设为入门前置条件。
- 复用 `answering.create_chat_model`、`agent_service.agent_session`、`agent_service.ask_agent` 和知识库业务函数；不另写一套 RAG 检索实现。
- `create_agent` 已经基于 LangGraph；当前只理解并使用其检查点能力，不手写 `StateGraph`、节点和边。
- 每次只推进一个知识点，提供短脚本、关键解释、实际输出观察和一个小练习；不一次生成整套后端框架。
- 当前已有的模型、数据库与 MCP 配置按需检查；不输出密钥，不把配置中的 MCP Token 当成任意用户的身份。
- 现有工作树包含大量未提交改动，不覆盖用户修改，不自动提交整个工作树。
- 文档中列出的命令均为后续执行方式，不能据此声称已经运行成功。

## 1. 当前起点

本次已阅读的本地代码：

- `answering.py:create_chat_model` 使用 `init_chat_model` 创建模型。
- `agent_service.py:agent_session` 经 `MCPAdapter` 加载工具，传给 `create_agent`。
- `agent_service.py:ask_agent` 使用 `ainvoke`、`thread_id` 和递归上限 12。
- `agent_session` 内创建 `InMemorySaver`；只有同一 saver 生命周期内的状态会保留，重建 session 或重启进程后不能依赖它恢复对话。
- 现有 `main()` 是两轮记忆示例，不是交互式 CLI，也没有演示完整知识库问题与流式输出。

因此，应在已有代码上逐层理解和扩展。已有实现不等于已经理解，也不等于本次验证了实际服务可用。

## 2. 学习与交付顺序

### Task 1：模型与消息——先看清一次模型调用

**Files:** 阅读 `answering.py`、`config.py`；新增 `examples/__init__.py`、`examples/langchain_model.py`、`docs/learning/langchain-backend-notes.md`。

**练习入口：** `python -m examples.langchain_model`，从项目根目录执行，使用项目虚拟环境的 Python。

- [ ] 先核对当前解释器与已安装 LangChain 版本，以及聊天模型配置是否齐全，不先升级依赖。
- [ ] 用现有 `create_chat_model(settings)` 发送 SystemMessage 与 HumanMessage；只打印消息类型、回答正文和供应商实际返回的 usage。
- [ ] 对比 `invoke` 与 `ainvoke` 的调用方式，解释同步 / 异步不改变“消息输入、模型消息输出”的基本契约。
- [ ] 用一次实际调用观察 AIMessage；若调用失败，记录真实异常与配置缺口，不输出 API Key。
- [ ] 用户练习：改变系统指令与用户问题，解释两者如何进入同一次模型请求。

**验收：** 能解释模型对象、消息列表、AIMessage、usage 的含义；知道 LangChain 是调用与编排框架，不是模型本身。若供应商不提供 usage，明确标记缺失。

### Task 2：工具调用——理解模型提出调用与程序执行的区别

**Files:** 新增 `examples/langchain_tools.py`；继续复用模型工厂。

**练习入口：** `python -m examples.langchain_tools`。

- [ ] 定义一个本地、无外部依赖的 `@tool`，例如 `lookup_demo_note(topic: str) -> str`，返回少量固定演示笔记；清楚标记为练习数据。
- [ ] 用 `bind_tools` 请求模型，打印返回的 `tool_calls`，观察工具名、参数与调用 ID。
- [ ] 手动执行一次被请求的工具，把带相同 tool_call_id 的 ToolMessage 送回模型，获得后续回答；如模型一次请求多个工具，逐个返回配对结果。
- [ ] 解释工具描述和参数 schema 的作用；无匹配主题时明确返回“未找到”，不编造检索结果。
- [ ] 用户练习：新增一个主题，观察模型何时调用工具、何时直接回答。

**验收：** 能讲清 `AIMessage.tool_calls → 执行函数 → ToolMessage → 模型继续回答`。手动循环只作为学习演示，实际项目继续采用 `create_agent`。

### Task 3：Agent——接回现有知识库

**Files:** 阅读 `agent_service.py`、`mcp_server.py`、`knowledge_service.py`；新增 `examples/langchain_rag_agent.py`。

**练习入口：** `python -m examples.langchain_rag_agent`。

- [ ] 先对比 Task 2 的手动循环和 `create_agent`，理解 Agent 代管了哪些步骤。
- [ ] 使用现有 `agent_session(settings, url, token)`，从 settings 构造 MCP 地址；不继续硬编码示例中的 localhost 端口。
- [ ] 核实所需模型、数据库和 MCP 服务连接；先在本地运行，远程设备操作另按设备目录规范执行。MCP 未启动时给出明确错误，不把连接失败判成 Agent 概念错误。
- [ ] 用当前 Token 所属用户的专用演示资料提出一个知识库问题，观察 `rag_search`、必要时 `rag_fetch` 和最终回答；不改造整套认证系统。
- [ ] 终端只展示可见回答、工具名与实际来源，不打印凭据或内部推理；保留原有 CLI 入口行为。

**验收：** 能解释 `model`、`tools`、`system_prompt` 的职责；可以展示一次真实工具调用与有来源的回答，并区分演示笔记练习和真实知识库访问。

### Task 4：记忆——理解 thread_id 与状态生命周期

**Files:** 在 `examples/langchain_rag_agent.py` 增加多轮演示；必要时新增 `tests/test_agent_memory.py`，使用可控伪模型验证状态隔离。

- [ ] 在同一个 `agent_session` 中复用 thread_id，连续发送两轮消息，观察状态保留；不要为每轮重新创建 saver。
- [ ] 使用新的 thread_id，确认其检查点不包含上一会话的消息；不能仅凭模型一句“我不知道”证明隔离。
- [ ] 退出并重建 session，观察 InMemorySaver 状态消失，解释“内存会话”与“持久化会话”的区别。
- [ ] 用户练习：追问上一轮答案中的对象，并检查状态中保存了哪些 HumanMessage、AIMessage 与 ToolMessage。

**验收：** 能解释 thread_id 是状态标识而非授权凭据；知道内存保存器适合当前学习阶段，PostgreSQL 检查点作为后续独立练习。

### Task 5：流式输出——在终端观察运行过程

**Files:** 新增 `examples/langchain_streaming.py`；若形成复用功能，再最小修改 `agent_service.py` 并增加 `tests/test_agent_streaming.py`。

**练习入口：** `python -m examples.langchain_streaming`。

- [ ] 根据当前已安装 SDK 验证流式接口，优先沿用可工作的事件方式；不为跟随文档示例强行升级整个依赖树。
- [ ] 对比“完整结果一次返回”和“助手可见正文逐步返回”，在终端显示文本与工具开始 / 完成状态。
- [ ] 过滤工具调用参数碎片、原始协议数据和模型内部推理；不要把所有流块无条件拼成答案。
- [ ] 模拟或注入一次工具失败、一次取消，检查终端明确显示结束原因，不输出伪成功标记。

**验收：** 无需网页即可展示流式问答；能区分文本流、状态事件与工具消息。新增过滤逻辑才增加相应行为测试。

### Task 6：middleware——用一个实际问题学习执行控制

**Files:** 新增 `examples/langchain_middleware.py`、`tests/test_agent_limits.py`；笔记追加到 `docs/learning/langchain-backend-notes.md`。

- [ ] 选择一个当前 SDK 支持的 middleware，练习限制每轮工具调用次数，并展示超限后的明确终止行为。
- [ ] 对比递归上限与工具调用预算；递归步数不能直接当成工具调用次数。
- [ ] 用可控工具与伪模型验证超限不会继续调用真实模型或检索；再用一条演示问题观察实际行为。
- [ ] 记录一页总结：框架提供什么，应用仍需负责什么；例如用户授权、真实来源校验和业务异常不能只交给提示词。

**验收：** 能在 `create_agent` 上扩展一个可解释、可验证的行为，不手写另一套图或 Agent 框架。

## 3. 现在不作为必做项的内容

以下内容保留为后续工程扩展，不阻塞上述学习顺序：

- Vue 问答页、SSE Web 协议、网页来源抽屉与响应式布局。
- Starlette 问答 API、多用户 Web 接入、数据库消息与检查点双写对账。
- PostgreSQL checkpointer、崩溃恢复、请求幂等和生产部署。
- 完整 40 题评测、LangSmith 云端接入、自定义 LangGraph 编排和多 Agent。

学习完成后再按兴趣选一个后续方向：继续后端 API 工程化，或做小型评测与检索改进；不要求同时开展。

## 4. 第一轮学习的最小完成标准

1. 终端能提出资料问题并获得有实际来源的回答。
2. 同一会话能追问，能解释更换 thread_id 与重建 saver 的差异。
3. 能展示文本流与工具状态，并说明错误如何结束。
4. 能解释一次完整调用链：消息 → 模型 → 工具请求 → 工具结果 → 回答。
5. 有一份简短学习笔记与实际运行记录，能区分学习示例和工程实现。

## 5. 执行方式与检查

每次先用几句话解释当前概念，再实现 / 运行一个短例子，让用户观察结果并完成一个小改动；用户要求时再继续下一项。不一次性交付全部练习代码，也不以搭建脚手架代替学习。

文档验证只检查文件内容与任务完整性。后续新增代码按实际风险验证：基础调用观察一次真实结果；状态隔离、流过滤与预算限制用确定性行为测试；真实 MCP / 模型测试明确记录环境、用量与未验证项。学习阶段不宣称生产可用。

## 6. 官方参考

- [Agents](https://docs.langchain.com/oss/python/langchain/agents)
- [Runtime](https://docs.langchain.com/oss/python/langchain/runtime)
- [Short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)
- [Streaming](https://docs.langchain.com/oss/python/langchain/streaming)
- [Middleware](https://docs.langchain.com/oss/python/langchain/middleware/overview)

本计划沿用本次会话已核对的官方文档。具体调用签名仍以实际安装版本的契约检查为准。
