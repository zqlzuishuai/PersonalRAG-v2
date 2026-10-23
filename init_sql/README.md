# PersonalRAG v2 数据库初始化

此目录只交付数据库结构，不包含后端、LangChain 问答实现或旧库迁移程序。SQL 由你在服务器手动执行；生成过程中没有在云端运行这些脚本。

## 文件及执行顺序

| 文件 | 用途 |
|---|---|
| `00_create_database.sql` | 创建独立新版数据库、owner/app/auth 角色及连接权限 |
| `01_schema.sql` | 一次性创建十张表、索引、复合外键、RLS、触发器和检索视图 |
| `03_verify.sql` | 事务内测试结构和关键行为，最后回滚所有测试数据 |
| `PLAN.md` | 本次交付范围与验证步骤 |
| `validation.json` | 本机独立临时数据库的验证结果；不代表云端已安装或压测通过 |

目标 PostgreSQL **18+**，服务器需已安装 `vector` 和 `pg_trgm` 扩展的文件。旧库使用 pgvector 0.8.7，本机验证版本另见 `validation.json`。

## 在服务器执行

先把整个 `personalrag-v2` 目录放到服务器一个 postgres 用户可读取的目录，例如 `/tmp/personalrag-v2`。不要把它放在 postgres 无法进入的 `/root` 目录下。

在服务器 shell 执行：

```bash
cd /tmp/personalrag-v2

# 按目前服务器 PostgreSQL 18 的绝对路径写出，避免混用其他版本客户端。
sudo -u postgres /usr/pgsql-18/bin/psql -X -v ON_ERROR_STOP=1 -d postgres -f 00_create_database.sql
sudo -u postgres /usr/pgsql-18/bin/psql -X -v ON_ERROR_STOP=1 -d personalrag_v2 -f 01_schema.sql
sudo -u postgres /usr/pgsql-18/bin/psql -X -v ON_ERROR_STOP=1 -d personalrag_v2 -f 03_verify.sql
```

三个命令均应退出成功。验收脚本末尾应显示 `PASS`。`03_verify.sql` 使用超级用户创建并回滚测试数据，再临时切换成应用/认证角色验证真实权限，不是仅用超级用户读表。

如果 `01_schema.sql` 报错，`ON_ERROR_STOP` 会中止，连接退出时该脚本的整个事务回滚。不要忽略报错继续下一步。

- `00` 可重复执行，但会拒绝所有者不符合预期的同名数据库或权限异常的新版角色。
- `01` 是首次安装脚本，故意拒绝已有的 `rag` schema，不会静默覆盖或清空已有结构。
- `01` 和 `03` 检查当前数据库名必须为 `personalrag_v2`，误连旧库时在实际建表/写测试数据前报错。
- `00` 不修改旧数据库的表、角色或密码；新角色名称均为 `personalrag_v2_*`。
- 创建完结构后还没有业务用户和原文数据，这是预期结果。

## 数据库角色和密码

| 角色 | 职责 |
|---|---|
| `personalrag_v2_owner` | NOLOGIN，结构所有者，后续迁移由管理员切换到此角色执行 |
| `personalrag_v2_app` | 后端/worker/MCP 的业务连接，受用户 RLS 限制 |
| `personalrag_v2_auth` | 认证专用连接，只能读取用户 ID、登录名、密码哈希、MCP 令牌哈希和账号状态 |

脚本没有预置密码，也不复用旧库密码。首次部署后交互设置两个 LOGIN 角色的密码：

```bash
sudo -u postgres /usr/pgsql-18/bin/psql -X -d personalrag_v2
```

然后在 psql 中输入：

```text
\password personalrag_v2_app
\password personalrag_v2_auth
\dt rag.*
\q
```

认证使用独立连接是为了在尚未识别用户身份时查询登录标识；不要为此放宽业务数据的 RLS。认证角色没有其他业务表权限。

## 表和常用检查

所有核心业务表位于 `rag` schema：

`users`、`folders`、`documents`、`document_versions`、`processing_runs`、`chunks`、`conversations`、`messages`、`answer_runs`、`citations`。

```sql
SELECT tablename FROM pg_tables WHERE schemaname='rag' ORDER BY tablename;
SELECT relname,relrowsecurity,relforcerowsecurity
FROM pg_class WHERE relnamespace='rag'::regnamespace AND relkind='r' ORDER BY relname;
```

`rag.searchable_chunks` 是额外的普通视图，不是第十一张业务表。它使用调用者权限，并自动排除未发布结果及软删除资料；调用方仍必须限制兼容的 embedding 配置。

## 应用连接必须设置用户上下文

应用端先认证用户，再在**每个事务**开始时设置已验证的 ID：

```sql
BEGIN;
-- 使用参数绑定，例如 SELECT set_config('app.user_id', %s, true)。
-- 下行示例 UUID 必须替换为已由服务端认证的真实用户 ID。
SELECT set_config('app.user_id', '00000000-0000-4000-8000-000000000001', true);
SELECT id,title FROM rag.documents WHERE deleted_at IS NULL;
COMMIT;
```

不设置上下文时，业务角色读取不到任何用户资料。`SET LOCAL`/`set_config(...,true)` 必须与查询在同一个显式事务中，避免连接池串用户。

共享数据库账号能设置其他 `app.user_id`；RLS 的前提是后端可信地完成认证并设置它。不要将数据库账号交给最终用户，不提供让客户端执行任意 SQL 的接口，也不要直接信任请求体中的 user_id。文件读取仍需应用校验用户归属。

`personalrag_v2_app` 不能创建/删除业务用户或禁用账号。初始业务用户由后续管理程序或管理员创建，`password_hash` 必须是实际密码散列，`mcp_token_hash` 是令牌 SHA256，不是数据库密码或云 API key。验收脚本中的虚拟账号最终全部回滚，不可拿来登录。

## 原文、版本和处理配置

- 原文不保存在数据库，`storage_key` 是以用户隔离的存储根目录为基准的相对键。SQL 拒绝绝对路径、Windows 盘符、反斜线和 `..` 路径段；后端仍应校验文件实际解析路径留在存储根目录。
- 推荐部署目录：`/var/lib/personalrag-v2/<user_id>/raw/` 和 `.../parsed/`。本 SQL 不会创建这些操作系统目录。
- 创建资料时先不设 latest/active 指针；原文文件就绪并写入版本后更新 `latest_version_id`。
- config_hash 和 content_sha256 由数据库生成，插入语句不要给这两个生成列赋值。
- 初始向量固定为 `vector(1024)`，使用 cosine HNSW 和 trigram GIN；无额外全文索引，无第二份 general_embedding。
- 新处理批次必须从 queued 开始。运行时设置 worker、租约和 started_at；插入分块前设为 running；结束时提交准确 chunk_count、解析产物键/哈希和 finished_at。
- 成功后再将资料 active_run_id 切至该批次。数据库检查批次成功且对应最新原文，旧任务晚完成不能覆盖新版本。
- worker 的 `FOR UPDATE SKIP LOCKED` 领取、租约失效回收、每批写入/发布前再次核对 worker 身份及有效期、重试退避，仍需后端实现；建表不等于处理程序已经完成。

最小配置形状示例（不含任何 API key）：

```json
{
  "parser": {"name": "text", "version": "1"},
  "chunker": {"name": "recursive", "size": 1000, "overlap": 100},
  "embedding": {
    "provider": "dashscope",
    "model": "qwen3.7-text-embedding-flash",
    "dimensions": 1024,
    "endpoint_type": "native",
    "input_template": "detail_content:",
    "normalize": true,
    "tokenizer": "explicit-tokenizer-identifier"
  }
}
```

模型字段是设计时使用的当前配置示例，实际接入前核对模型可用性。改变模型、端点类型、输入模板或分块规则都会产生不同配置哈希；不要只按维度混用向量。

## 删除和重试边界

- 默认更新 `documents.deleted_at` 软删除；历史引用仍保留。
- 物理清理先预览引用/文件影响，清理 answer_runs 的引用上下文，将 citations 的 `source_status` 改为 deleted，同时将 document_id/version_id/chunk_id 设为 NULL、quote 设为空字符串、locator 设为 `{}`。
- 然后清空 documents 的 active/latest 指针，按 chunks → processing_runs → document_versions → documents 的顺序清理；存在其他引用时外键会阻止操作。
- 最后删除已经没有版本引用的原文文件。上述操作由后续管理流程实现，本目录不包含批量删除脚本。
- 已完成回答和引用不能原地改写/改指新版。重新生成创建新的回答执行记录及助手消息；删除来源不自动删除旧回答正文。
- 文件夹祖先循环、原文提交与文件回收协调、消息顺序分配、问答末尾引用编号校验、并发删除与问答发布协调都仍是后端事务/应用逻辑职责。

## 验证范围

本机验收使用无网络的临时容器，不读取现有个人数据库数据。它验证 PostgreSQL 能执行 DDL，以及关键权限、关联、唯一性、发布和历史保护规则；不代表云端已执行、文件备份恢复已通过、LangChain 已接入或并发性能已达标。

官方依据：[RLS](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)、[复合外键和 NULLS NOT DISTINCT](https://www.postgresql.org/docs/18/sql-createtable.html)、[security_invoker 视图](https://www.postgresql.org/docs/18/sql-createview.html)。
