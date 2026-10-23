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
