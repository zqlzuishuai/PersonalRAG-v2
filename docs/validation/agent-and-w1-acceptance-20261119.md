# 2026-11-19 Agent 与 W1 验收

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| 现有 Python 回归 | 79 项通过 | `python -B -m unittest discover -s tests -v` |
| MCP HTTP 认证和工具调度 | 通过 | 本机 Uvicorn、实际 MCP Streamable HTTP 和 LangChain MCPAdapter。无 Token 和无效 Token 均返回 `401`，有效测试 Token 下依次执行 `rag_search`、`rag_fetch`。认证查询、检索数据和聊天模型用测试替身。 |
| Agent 流式问答正常结束 | 失败 | 真实 LangGraph 图发出 `None` 更新后，`stream_agent` 抛出 `AttributeError`。 |
| W1 持久化答案、引用、读回与重放 | 通过 | 本机 `15433` 恢复连接后，用测试账号和真实模型完成落库、独立读回、重放及跨账号拒绝。已清理本次会话和关联记录。[实测结果](w1-persistence-20261119.json) |

## Agent 流式问答中断

在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -B -m tests.acceptance_agent_mcp
```

复现版本为 LangChain `1.4.7`、LangGraph `1.2.16`、MCP `2.3.0`、FastMCP `4.1.4`。用例启动临时回环服务，退出时关闭。它先直接消费真实 Agent 图的 `updates`，再通过 `stream_agent` 重跑同一脚本化问答。

直接读取图时，两次工具调用正常执行。无工具调用的最终回答还产生了 `{"ToolCallLimitMiddleware.after_model": null}`。`stream_agent` 随后在 `agent_service.py` 的 `update.get("messages", [])` 处失败。复现中正文已输出，生成器仍以异常退出，调用方无法按正常完成结束该轮。

修复后的复验以脚本退出码 `0` 为通过条件。两项工具请求与结果需要按调用 ID 成对出现，最终正文包含样例事实及片段 ID，而且迭代正常结束。真实模型对补查时机的选择和真实数据库访问需要单独验收。
