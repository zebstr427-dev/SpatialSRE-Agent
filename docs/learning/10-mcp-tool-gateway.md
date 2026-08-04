# 第 10 课：建立 MCP Tool Gateway

完成日期：2026-08-04

对应范围：`feat(aiops): add MCP tool gateway`

## 企业问题

原来的 Planner、Replanner 和 Executor 分别读取本地工具与 MCP 工具，Executor 再通过 `ToolNode` 直接执行。工具发现和执行入口分散后，后续加入风险等级、身份、策略和人工审批时容易遗漏某条路径；本地工具与 MCP 工具的超时、重试和错误语义也不一致。

本课在 Durable AIOps 主链建立统一 Tool Gateway。Planner 和 Replanner 从同一注册表获取工具描述，Executor 只能通过 Gateway 执行工具；Gateway 负责重名拒绝、标准结果、超时、有限尝试和审计通知。旧 `RAGAgentService` 保持兼容，不在本课迁移范围内。

## 本课目标与完成结果

- 目标：建立统一工具注册与执行边界，覆盖 registry、统一路由、标准错误、超时、重试能力和审计钩子。
- 实际完成：本地与 MCP 工具统一注册并拒绝重名；Planner、Replanner、Executor 接入同一 Gateway；执行结果统一为 `ToolExecutionResult`；覆盖找不到工具、超时、执行异常、有限尝试、同步或异步审计钩子及任务取消传播。
- 明确未覆盖：工具风险等级、写操作 dry-run、身份与权限、策略决策、人工审批、幂等键、exactly-once、真实外部 MCP 服务的端到端调用和审计钩子持久化失败的强一致处理。

## 设计与实现

```text
Planner / Replanner
    -> create_tool_gateway()
        -> local tools + MCP tools
            -> ToolRegistration registry
                -> list_tools() -> LLM prompt

Executor
    -> create_tool_gateway(audit_hook=record_tool_call)
        -> invoke(call_id, name, arguments)
            -> name lookup
            -> JSON-safe argument check
            -> asyncio.wait_for
            -> bounded attempts
            -> ToolExecutionResult
                -> ToolCallAuditRecord
                -> ToolMessage / failed ExecutedStep
```

`ToolRegistration` 保存工具来源、单次超时、最大尝试次数和重试延迟。注册表使用工具名作为唯一键，本地工具与 MCP 工具同名时立即抛出 `ValueError`，避免 LLM 看见一个名称却由运行时随机选择实现。

`ToolExecutionResult` 把成功与失败归一为只含稳定值的数据契约，包括调用 ID、工具名、来源、参数、状态、结果、错误码、尝试次数和起止时间。当前错误码为 `tool_not_found`、`tool_timeout` 和 `tool_execution_failed`。

Executor 通过审计钩子把 Gateway 结果映射回第 8 课的 `ToolCallAuditRecord`。任一工具最终失败时，当前执行步骤标记为失败；全部成功时才把 `ToolMessage` 交给 LLM 生成步骤摘要。多个工具暂时串行执行，以保持确定的调用与审计顺序。

## 为什么这样设计

- 统一边界比在三个节点分别添加控制逻辑更容易保证后续策略不会被绕过。
- 标准结果让调用方基于稳定错误码判断失败类型，不需要了解每个工具或 MCP SDK 的异常结构。
- `asyncio.wait_for` 给每次尝试设置时间上限；循环次数由注册信息限制，避免无限等待或无限重试。
- 默认 `max_attempts=1` 是安全取舍。第 11 课识别只读、写入和高风险工具前，不默认重试可能已经产生副作用的操作。
- 只捕获 `Exception`，不吞掉继承自 `BaseException` 的 `CancelledError`，因此应用关闭和工作流取消仍能及时传播。
- Gateway 使用无旧重试拦截器的新 MCP client，避免旧 MCP 拦截器与 Gateway 重试相乘；代价是当前每个 AIOps 节点仍会重新建立工具注册表。

审计钩子当前属于尽力通知：钩子异常会记录日志，但不会改变已经完成的工具结果。它不等于合规级不可丢失审计，后续仍需要持久化 outbox、告警或 fail-closed 策略。

## 验证证据

```powershell
.\.venv\Scripts\pytest.exe tests/unit/test_tool_gateway.py tests/unit/test_aiops_executor.py -q
.\.venv\Scripts\pytest.exe -m "not postgres" -q
.\.venv\Scripts\pytest.exe -m postgres -q
.\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\ruff.exe check app/agent/tool_gateway.py app/agent/aiops/planner.py app/agent/aiops/replanner.py app/agent/aiops/executor.py tests/unit/test_tool_gateway.py tests/unit/test_aiops_executor.py
.\.venv\Scripts\python.exe -m compileall -q app tests
git diff --check
Invoke-RestMethod http://127.0.0.1:9900/health | ConvertTo-Json -Depth 6
```

实际结果：聚焦测试 `7 passed`，非 PostgreSQL 回归 `47 passed`，PostgreSQL 集成 `2 passed`，完整测试 `49 passed`。Gateway 聚焦覆盖率为 `86.09%`，Executor 为 `91.84%`。Ruff、compileall 和 diff 检查通过；diff 检查只有现有工作区的 LF/CRLF 转换提示，没有 whitespace error。

运行时健康接口返回 HTTP `200`，整体状态为 `healthy`，Milvus 与 PostgreSQL checkpoint store 均为 `connected`。PowerShell 中中文消息出现显示乱码，但 JSON 结构、状态码和关键英文状态字段正确。

## 排错记录

首次静态检查报告 2 个 `I001` 和 4 个 `W292`。根因是复制代码后导入分组顺序不符合 Ruff 规则，且 4 个新增或整体替换的文件缺少末尾换行。对第 10 课文件执行定向 Ruff 修复后，6 个问题全部消失；随后重新运行 Ruff、compileall 和 diff 检查均通过。

运行时健康响应中的中文消息显示为乱码。该现象位于 Windows PowerShell 输出编码边界，不影响 HTTP 200、JSON 字段解析或依赖健康状态，因此没有修改应用业务编码。

## 常见错误

### 在 Executor 外保留直接工具执行入口

如果 Planner、Replanner 或新的节点仍能直接调用 Agent 工具，后续 Gateway 上的风险、策略和审批控制就可能被绕过。当前 Planner 的知识库预加载仍是内部检索路径，不属于 LLM 选择的 Executor 工具调用；这一边界需要在后续证据与策略课程继续收敛。

### 把重试当成 exactly-once

超时只说明调用方没有按时获得结果，不代表服务端没有执行。对写工具直接重试可能重复变更，因此本课只提供有限尝试机制，生产默认仍为一次尝试。

### 捕获 BaseException

`CancelledError` 是调度和关闭信号。将它转换成普通工具失败会让任务无法及时取消，还可能在应用关闭期间继续执行工具。

### 只记录最终 LLM 摘要

摘要经过模型改写，不能替代原始执行结果。Gateway 审计钩子保存标准执行结果，LLM 摘要继续由 `past_steps` 单独保存。

## 秋招知识点

- Gateway 模式：用单一入口统一异构后端的发现、执行和横切能力，为权限、策略、审计和限流提供强制执行点。
- 失败语义：错误码是稳定机器契约，错误消息用于人类排查；超时、找不到工具和执行异常不能混为一种失败。
- 超时与取消：超时限制单次等待，取消终止上层任务，两者的触发者和传播语义不同。
- 重试边界：重试提高临时故障恢复能力，但会放大非幂等操作的副作用风险，必须与风险分类和幂等协议结合。
- 分层验证：Gateway 单元测试证明契约和边界，全量回归证明兼容性，健康接口证明应用及持久化依赖能够装配运行。

## 面试问答

**问：为什么 Agent 项目需要 Tool Gateway，而不是把工具列表直接绑定给 LLM？**

答：场景是 Planner、Replanner 和 Executor 都要接触本地与 MCP 工具；风险是入口分散后，超时、审计、权限或审批只能重复实现并可能被绕过。我建立统一 registry，用 Gateway 按名称执行工具并返回标准结果，Executor 通过审计钩子保存调用记录。聚焦 7 个测试覆盖重名、成功、找不到、异常、超时、有限尝试和取消传播，全量 49 个测试通过。边界是第 10 课只建立执行入口，风险和授权决策从第 11 课开始加入。

**问：为什么默认不自动重试两次或三次？**

答：超时后服务端可能已经完成写操作，只是响应没有返回。当前没有工具风险和幂等元数据，默认重试会把可用性优化变成重复副作用风险。因此 Gateway 支持显式 `max_attempts`，测试证明有限重试机制有效，但生产默认保持一次尝试；下一课将根据只读、写入和高风险等级决定允许行为。

## 下一课衔接

第 11 课将在 ToolRegistration 上增加风险等级和执行元数据。统一 Gateway 将据此允许只读工具执行、对写工具提供 dry-run，并阻止未经控制的高风险操作。
