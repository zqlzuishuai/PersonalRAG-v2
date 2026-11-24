# RAG 后端与 LangChain Agent

## 现状与目标

固定 RAG 是首版网页问答路径；MCP 向外部客户提供两个只读知识工具，Agent 可经 MCP 按需搜索或补查。Web 和 MCP 共享数据层；Web 固定回答直接调用业务函数，不把 MCP 当作内部代理。当前按[产品计划](PRODUCT.md)完成 Web 问答、原文编辑、MCP 联调。Agent 学习和对照实验随后继续。

锁文件记录 LangChain 1.4.7、langchain-core 1.7.0、LangGraph 1.2.16。`create_agent` 使用 LangGraph 运行图；当前已有内存检查点和流式事件，不需要为了演示另写 `StateGraph`。

## 数据与调用流程

| 环节 | 入口与语义 |
| --- | --- |
| 原文件与版本 | [documents.py](../documents.py) 的 `upload_bytes` 写不可变原文快照、登记版本，最后更新 `latest_version_id`。原文件存储和数据库提交各有边界；按哈希复用最新版本时也会检查文件完整性。历史原文只读，在线编辑会新增文件版本（待实现）。 |
| 处理与发布 | [processing.py](../processing.py) 的 `process_version` 创建或复用任务；先校验原文，解析、切块、向量化，成功后写片段，并确认仍是最新版本才更新 `active_run_id`。处理未结束或失败时继续使用旧的已发布版本。同步任务的超时、提交不确定和人工恢复约定见[项目 README](../README.md)。 |
| 召回与重排 | [retrieval.py](../retrieval.py) 的 `hybrid_recall` 在 `rag.searchable_chunks` 上结合向量与 BM25 排名，用 RRF 融合；[rerank.py](../rerank.py) 随后按问题和片段做重排。Web 搜索和 MCP 使用 [knowledge_service.py](../knowledge_service.py) 的 `search_knowledge`；重排后再次核对片段仍可见。BM25 及数据库初始化见[数据库说明](../init_sql/README.md)和[BM25 配置](../init_sql/BM25.md)。 |
| 固定问答 | [answering.py](../answering.py) 的 `generate_system_message` 直接跑混合召回和重排，向模型发送当前问题及资料，返回回答和来源。`[n]` 映射到 `sources[n-1].chunk`；编号范围通过不证明语义上能支持结论。它不读取先前会话内容。 |
| 业务持久化 | [conversations.py](../conversations.py) 创建会话；[chat_service.py](../chat_service.py) 的 `ask_question` 和 [answer_runs.py](../answer_runs.py) 保存问题、运行状态、助手回答与实际引用；按当前用户读取，`client_request_id` 重放应读已有结果。消息和引用属于业务数据库；Agent 检查点保存图、工具及上下文状态，是不同用途。Web 持久化链路仍需实测。 |
| MCP 与身份 | [mcp_server.py](../mcp_server.py) 提供 `rag_search`、`rag_fetch`；用户由 [auth_http.py](../auth_http.py) 验证的 Bearer 凭据确定，工具参数不接收用户 ID。Web 则使用会话身份。两端依赖用户事务、资源归属及数据库约束。 |
| LangChain Agent | [agent_service.py](../agent_service.py) 的 `agent_session` 装配 MCP 工具、内存检查点和工具调用限制；`ask_agent` 一次性返回，`stream_agent` 用 `async for` 提供可见正文、工具请求和工具结果，结果通过调用 ID 配对。`thread_id` 是同一个 saver 中的状态键，不是身份；重建 saver 或重启失去已有图状态。 |

区分两个预算：`run_limit=3` 按单次调用累计工具请求，`recursion_limit=12` 限制图推进步骤。单批超限在本批执行前报错，不撤销前一批已执行的调用。终端取消异常向上传播，正常结束标记放在成功分支。流里的「已请求工具」也不代表工具函数实际执行。

## 如何复现与已经验证的范围

在隔离环境准备一份 UTF-8 Markdown，含可核对的虚构事实，如「蓝杉项目的归档编号为 QC-7319」。使用已授权测试账号：

1. 调用 `upload_bytes`，记录文档和文件版本 ID；用该版本调用 `process_version`，确认 `status=succeeded` 且 `is_published=true`。
2. 提问「蓝杉项目的归档编号是什么？」；调用 `generate_system_message`，核对回答中的结论、引用编号、来源版本和原文。再问文中没有的负责人，检查没有编造，也没有把「没查到」说成「不存在」。
3. 产品下一步改走 `create_conversation → ask_question → get_answer_run_result`，核对持久化结果及引用，然后接入 Web。MCP 协议联调用 [mcp_client.py](../mcp_client.py) 验证握手、工具列表、搜索和按 ID 读取，再用实际客户复验。使用新的测试样例时，明确写入目标和资料是否保留。

| 证据 | 结果与局限 |
| --- | --- |
| [2026-11-18 真实入库与问答](validation/stage1-rag-sample-20261118.json) | 新样例从空测试账号上传到发布；真实 PostgreSQL、embedding、混合召回、重排与模型回答跑通，并核对到本次文件版本。样例有意保留。不代表持久化问答、Web 或 MCP 已通过。 |
| [2026-11-18 证据不足](validation/stage2-insufficient-evidence-20261118.json) | 同一真实资料的一道问题未编造负责人；回答的附带事实有原文依据。未覆盖零召回和其他问题。 |
| 离线回归 | 历次核对的 `test_agent*.py` 有 5 项通过（工具限额 3、流事件 2）；`test_answering_citations.py` 6 项、`test_processing.py` 12 项通过。真实处理故障和跨用户访问仍需按产品计划验收。旧流式实验用假模型，不能作为模型供应商输出流能力的证明。 |

从项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_agent*.py' -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_answering_citations.py' -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p 'test_processing.py' -v
```

## 产品交付后：学习、评测及演示

- [ ] 同语料、同模型，准备 8 道题（3 单跳、3 可能需要补查或读取原文、2 证据不足）。运行前标记预期事实及来源；两条路径对每题独立运行，记录答案、证据支持性、耗时和实际工具执行。结果只说明这 8 个案例。
- [ ] 选一个实际失败做最小修正，以原题和两道原本正确的题验收。例如引用无法核对时，在本轮按真实工具证据分配引用编号，校验归属和有效性；避免把中间工具事件等同于最终提交结果。
- [ ] 整理三分钟演示：新文件入库、原文引用、何时用固定 RAG 或 Agent、失败案例、改动证据及局限。对外报告记录代码版本、资料版本、模型及参数；用量缺失写未提供，不用字符数代替。
- 后续可把召回评测细化为向量 / 混合 / 混合加重排，报告 Hit@k、Recall@k、MRR 和耗时；语义正确性仍人工核对，保留独立样例集，按需做追踪。只有确需多轮上下文、重启恢复或分支编排时再验证持久化检查点、来源重新授权、成功提交与检查点对账、稳定流协议；这些不是当前交付门槛。
