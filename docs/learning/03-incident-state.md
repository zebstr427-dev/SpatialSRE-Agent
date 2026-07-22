# 第 3 课：用 TDD 设计 IncidentState

对应提交：`150bf3d feat: introduce typed incident state`

## State 是 Agent Runtime 的持久化协议

LangGraph checkpoint 保存的不是 Python 调用栈，而是每个 superstep 后的图状态、待执行节点和相关元数据。因此 State 一旦持久化，就类似数据库 schema，必须稳定、可演进、可审计。

`IncidentState` 的核心字段分为四组：

- 身份：`incident_id`、`trace_id`、`session_id`。
- 业务：`severity`、`status`、`input`、`response`、`error`。
- 过程：`plan`、`past_steps`、`evidence`。
- 时间：`created_at`、`updated_at`。

`ExecutedStep` 替代旧的 `(step, result)` 元组，补充执行状态和起止时间。后续做失败回放、耗时统计和审计时不需要猜测元组位置。

## Reducer 的意义

```python
past_steps: Annotated[list[ExecutedStep], operator.add]
evidence: Annotated[list[EvidenceRecord], operator.add]
```

LangGraph 节点返回的是状态增量。没有 reducer 时，新值覆盖旧值；使用 `operator.add` 后，每个节点只返回本次新增记录，框架负责合并历史。

注意：节点必须只返回新增项。若每次返回完整历史，reducer 会造成重复数据。

## 序列化边界

checkpoint 中只放字符串、数字、布尔、`None`、列表和字典。不要存：

- 数据库连接、HTTP Client 或 MCP Session。
- Pydantic/ORM 复杂对象。
- Exception 实例、协程、闭包。
- 依赖任意代码执行才能反序列化的对象。

## 验证命令

```powershell
.\.venv\Scripts\pytest.exe tests/unit/test_aiops_history.py tests/unit/test_aiops_package.py -q
```

## 常见错误

### 恢复后报序列化错误

先打印 state 每个字段的 `type()`，通常是节点把第三方 SDK 对象直接放进了 checkpoint。应在工具边界转换成安全字典。

### past_steps 重复

检查节点是否在 reducer 字段中返回了“旧历史 + 新记录”。正确返回值只能包含新记录。

## 面试问答

**问：session_id、incident_id、trace_id 为什么不能合并？**

答：一个会话可能连续处理多个故障，一个故障也可能有多次执行尝试。incident 是持久化隔离单位，trace 是一次链路，session 只表示交互上下文。

**问：TypedDict 能防止数据库里出现错误数据吗？**

答：不能。TypedDict 主要提供静态检查。真正的边界还要依靠构造函数、节点约束、序列化器和测试。
