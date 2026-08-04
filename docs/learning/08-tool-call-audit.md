# 第 8 课：持久化工具调用审计

完成日期：2026-08-03

对应范围：`feat(aiops): persist tool-call audit history`

## 企业问题

原 executor 只把 LLM 生成的最终步骤摘要写入 `past_steps`。摘要无法回答某次工具调用使用了什么参数、返回了什么原始结果、成功还是失败，也无法通过调用 ID 将请求与结果可靠关联。进程重启后，这些信息更无法用于审计、复盘和后续评测。

本课把工具调用建模为稳定状态契约，并随 LangGraph checkpoint 写入 PostgreSQL。边界是应用级审计：它不提供密码学防篡改、敏感字段脱敏、长期归档策略或工具副作用的 exactly-once 保证。

## 本课目标与完成结果

- 目标：定义 checkpoint-safe 的工具审计 schema，并在 executor 成功和失败路径中写入。
- 实际完成：记录调用 ID、工具名、步骤、参数、实际工具结果、状态和起止时间；通过 reducer 累积；跨连接池恢复后字段和 incident 隔离保持完整。
- 明确未覆盖：审计签名、字段脱敏、保留周期、幂等执行、重试策略和统一 Tool Gateway。

## 设计与实现

`ToolCallAuditRecord` 只包含字典、字符串等稳定值。`create_tool_call_audit_record()` 在状态入口使用 `json.dumps()` 预检参数，把第三方对象或循环引用转化为稳定的 `ValueError`，避免错误延迟到 checkpoint 写入阶段。

```text
AIMessage.tool_calls
    -> 按 tool_call_id 匹配 ToolMessage
        -> create_tool_call_audit_record
            -> IncidentState.tool_calls (operator.add)
                -> AsyncPostgresSaver
```

executor 保存 `ToolMessage.content`，而不是后续 LLM 的总结。`ToolMessage.status == "error"` 映射为 `failed`；`ToolNode` 直接抛异常时，也会为已经确定的调用写入失败记录。结果按调用 ID 配对，不能依赖返回列表顺序。

## 为什么这样设计

- 结构化 TypedDict 比保存整个 `AIMessage` 更稳定，也更适合 API、checkpoint 和评测消费。
- reducer 使用追加语义，多个执行节点不会覆盖历史记录。
- 单元测试隔离 LLM、MCP 和 ToolNode，使成功、错误和异常路径确定可复现。
- PostgreSQL 测试重建连接池后再读取，证明数据来源是 checkpoint，而不是同进程内存对象。

审计记录只能说明应用观察到的执行过程。若工具已经产生外部副作用，但进程在 checkpoint 前崩溃，仍可能发生重复执行，需要后续幂等键、执行租约或 outbox 协议解决。

## 验证证据

```powershell
.\.venv\Scripts\pytest.exe tests/unit/test_aiops_executor.py tests/unit/test_incident_state.py -q
.\.venv\Scripts\pytest.exe -m "not postgres" -q
.\.venv\Scripts\pytest.exe -m postgres -q
.\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\ruff.exe check $lesson8Files
.\.venv\Scripts\python.exe -m compileall -q app tests
git diff --check
```

实际结果：聚焦测试 `9 passed`，非 PostgreSQL 回归 `34 passed`，PostgreSQL 集成 `2 passed`，完整测试 `36 passed`；Ruff、compileall 和 diff 检查通过。

应用级验证使用 Selector event loop 启动临时 Uvicorn：健康接口返回 `200`，Milvus 与 PostgreSQL 均为 `connected`；AIOps SSE 以 `complete` 结束；incident 查询返回 `200` 和 5 条工具审计，每条均包含字典参数、非空结果、状态和起止时间。验证生成的 checkpoint 已删除，临时服务已关闭。

## 排错记录

首次使用 FastAPI `TestClient` 验证 lifespan 时，Psycopg 报错无法在 Windows `ProactorEventLoop` 上运行，连接池最终超时。根因不是审计序列化，而是测试客户端创建了与 Psycopg 不兼容的事件循环。

修正方式是遵循项目真实启动入口的语义，在 `asyncio.SelectorEventLoop` 上启动临时 Uvicorn，再通过 HTTP 完成验证。第二次运行健康、SSE、checkpoint 查询和资源关闭均成功。

Ruff 还发现 3 个导入分组问题。只对本课 5 个 Python 文件执行修复和格式化，避免把历史代码风格债混入本课变更。

## 常见错误

### 按列表位置关联工具结果

工具可能并行执行或改变返回顺序。必须使用 `AIMessage.tool_calls[].id` 与 `ToolMessage.tool_call_id` 关联。本课测试故意反转 ToolMessage 顺序来证明这一点。

### 把最终 LLM 摘要当成工具结果

摘要经过模型改写，不能作为原始审计证据。审计保存实际 `ToolMessage.content`，步骤摘要仍由 `past_steps` 单独承载。

### 把 checkpoint 当成 exactly-once

checkpoint 记录状态进度，不会自动消除外部工具的重复副作用。涉及写操作时仍需要业务幂等协议。

## 秋招知识点

- 审计数据建模：持久化字段一旦进入 checkpoint 或 API，就应被视为长期兼容契约。
- 请求结果关联：异步系统必须依赖稳定 correlation ID，而不是到达顺序。
- 失败语义：工具返回错误和执行器抛异常是不同路径，都要留下可查询记录。
- 序列化边界：在构造状态时尽早拒绝不安全值，比数据库写入阶段才失败更容易定位。
- 分层测试：单元测试证明状态转换，真实 PostgreSQL 测试证明持久化，HTTP 运行证明应用装配。

## 面试问答

**问：你如何给 Agent 增加可审计的工具调用链？**

答：场景是生产 Agent 需要复盘每次工具请求和实际结果；风险是只保存 LLM 总结会丢失参数、错误和关联关系。我定义只含基础类型的审计 schema，用调用 ID 配对 `AIMessage` 与 `ToolMessage`，通过 reducer 追加到 LangGraph state，并写入 PostgreSQL checkpoint。单元测试覆盖乱序结果和异常，集成测试覆盖连接池重建，真实 HTTP 验证得到 5 条审计。边界是它还不具备防篡改、脱敏和 exactly-once 能力。

**问：为什么不能按 tool call 和 tool message 的列表位置配对？**

答：并发、重试或框架实现都可能改变完成顺序。位置是偶然关系，调用 ID 才是协议关系。本课测试把成功和失败的 ToolMessage 反向返回，仍能得到正确状态和结果。

**问：checkpoint-safe 是否等于安全？**

答：不等于。checkpoint-safe 只表示当前序列化器能稳定保存和恢复这些值。安全还需要参数脱敏、访问控制、审计完整性、保留策略和密钥管理。

## 下一课衔接

第 9 课将建立 Initial EvalOps。稳定的工具审计记录可以直接用于计算工具选择准确率、调用成功率、失败分布和用例回放结果。
