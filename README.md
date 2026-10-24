# PersonalRAG v2

原文保存在 `PERSONALRAG_RAW_STORAGE_DIR`，数据库仅保存元数据与相对路径。

## 上传原文

先修改 `documents.py` 中 `main()` 的 `file_path`、`user_a` 和 `document_id`，再直接运行脚本：

```powershell
.\.venv\Scripts\python.exe documents.py
```

`document_id = None` 表示新建资料。为已有资料增加版本时，改为 `document_id = UUID("已有资料的 document_id")`。

上传返回 `UploadResult`，包含 `document_id`、`version_id`、`version_no`、`storage_key` 和两个新增标记。

`document_id` 为 `None` 时每次运行都会创建新资料；文件名相同不会自动合并。与最新版本内容相同且已有原文完整时复用该版本；A→B→A 会保留三个版本。每个版本使用独立路径，不覆盖历史文件。

只上传和登记原文，不会自动解析、切块或生成向量。`upload_file` 中的用户 ID 必须来自已认证身份；它本身不是认证接口。

## 本地回归测试

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

测试用模拟数据库边界和真实临时文件验证上传逻辑，不连接实际数据库；不能据此断言 PostgreSQL 的 RLS、外键或并发行为已经实测通过。

`main.py` 是另一个手动数据库检查：使用其中配置的两个现有用户，验证跨用户目录关联被外键拒绝，并清理本次随机 ID 的测试记录。运行它会连接 `.env` 指定的数据库。

## 失败处理

SQL 执行阶段失败会清理本次新增原文；提交阶段连接异常时，服务端可能已经提交，因此保留文件并抛出异常。此时先核对数据库和文件，再决定重试，尤其首次上传不能盲目重试以免产生重复资料。进程中断也可能留下孤立文件；当前没有自动清理任务。

旧实现造成的缺失或覆盖原文无法自动恢复。重复上传发现历史文件缺失或哈希错误时会报错，避免误报上传成功。


## 同步执行处理任务（学习版本）

`processing.py` 不带参数仍只创建 queued 任务。执行已经创建的任务：

```powershell
.\.venv\Scripts\python.exe processing.py 这里替换成已创建的任务UUID
```

调用用户取自当前 `main()` 中的 `user_id`。函数调用方式为：
`execute_processing_run(settings, user_id, run_id)`。
执行命令会连接真实数据库，将文档片段发送到 `.env` 中
`DASHSCOPE_BASE_URL` 指定的接口，并使用 `DASHSCOPE_API_KEY`，可能产生费用。
`embedding.py` 通过 LangChain `OpenAIEmbeddings` 调用兼容接口；
模型和 1024 维配置取自任务记录，而不是在执行时另选模型。

任务先由 queued 变为 running，在数据库事务外读取并校验原文、切分、调用 API。
再用一个事务写入全部 chunks、结束任务，并仅在版本仍是最新版本时发布结果。
片段位置是解析后 UTF-8 文本中的 Python 字符下标，采用左闭右开区间，
不是字节偏移，也不是原始二进制文件中的偏移。
空白文档允许成功产生零个片段；token_count 暂不填写，避免把字符数冒充 token 数。

目前只支持 UTF-8/UTF-8-BOM 文本和递归字符切分；不会执行 JSON/PDF 专用解析。
本版本是小文件同步流程，租期为 15 分钟，没有心跳续租、自动重试或崩溃恢复器。
超过租期会拒绝保存结果；进程中断可能留下 running 任务，需要人工检查。
失败任务不能直接再次执行，需确认状态后另行实现重试；不要反复创建相同配置的任务。
若提交结果不确定，先核对数据库状态再操作。解析快照在失败时可能成为孤立文件，
目前会保留以免误删已提交结果引用的文件，没有自动垃圾回收。

本地测试使用模拟数据库/API及真实临时文件，另有实际 LangChain 客户端结合
MockTransport 的请求格式和分批测试；不会连接云端数据库或调用外部模型。
这些检查不能代替真实 PostgreSQL 的 RLS、触发器和并发验证。

参考：[LangChain embedding 集成](https://docs.langchain.com/oss/python/integrations/embeddings/openai)、
[阿里云向量接口](https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api)。
