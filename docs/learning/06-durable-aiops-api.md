# 第 6 课：接入 Durable AIOps API

对应提交：`a158d1c feat(durable-runtime): persist incident workflows`

## ID 语义

旧代码把 `session_id` 直接作为 LangGraph `thread_id`。这样同一用户连续诊断两个故障时会共享 checkpoint，造成状态串线。

新映射为：

```text
LangGraph thread_id = incident_id
```

`session_id` 继续保留以兼容调用方，但只作为业务元数据。未传 `incident_id` 时，HTTP 层生成 UUID 并通过第一条 SSE 事件返回。

## SSE 可观测字段

每个正常、完成或错误事件都附带：

```json
{
  "incident_id": "incident-456",
  "trace_id": "7f...",
  "sequence": 1,
  "timestamp": "2026-07-22T06:00:00+00:00"
}
```

- `incident_id`：关联持久化状态。
- `trace_id`：关联一次执行的所有日志和工具调用。
- `sequence`：检测前端丢事件或乱序。
- `timestamp`：计算阶段耗时并支持回放。

旧事件的 `type`、`stage`、`message`、`response/diagnosis` 不删除，保证向后兼容。

## API 验证

发起诊断：

```powershell
$body = @{session_id="session-123"; incident_id="incident-456"} | ConvertTo-Json
Invoke-WebRequest http://127.0.0.1:9900/api/aiops -Method Post -ContentType application/json -Body $body
```

查询状态：

```powershell
Invoke-RestMethod http://127.0.0.1:9900/api/incidents/incident-456 | ConvertTo-Json -Depth 10
```

未知 incident 返回 HTTP `404` 和 `{"detail":"Incident not found"}`。

健康检查现在同时返回：

```text
data.milvus.status
data.checkpoint_store.status
```

任一不是 `connected`，整体返回 HTTP `503`。

## 测试命令

```powershell
.\.venv\Scripts\pytest.exe tests/unit/test_aiops_service.py tests/unit/test_aiops_api.py tests/unit/test_health_api.py -q
```

## 常见错误

### 状态查询一直 404

检查 POST 响应中的 `incident_id`，不要用 `session_id` 查询。再检查 PostgreSQL checkpoint 表是否有对应 thread。

### complete 事件缺少 trace_id

通常是兼容层重新构造事件时丢弃公共字段。应先展开原事件，再覆盖兼容字段。

## 面试问答

**问：sequence 能实现 exactly-once 吗？**

答：不能。sequence 只帮助检测和排序。Exactly-once 还需要幂等键、执行租约、原子状态转换和工具侧幂等，本阶段明确不实现。

**问：为什么 GET 读取 graph state，而不是直接查 checkpoints 表？**

答：表结构属于 LangGraph checkpointer 的内部实现。通过 `aget_state` 读取可保持框架兼容，并正确处理 checkpoint namespace 和反序列化。
