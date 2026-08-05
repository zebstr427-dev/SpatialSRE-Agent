# 第 14 课：可恢复的人类审批

## 实现位置与功能

- `app/agent/approval.py`：审批请求、终态决策和 LangGraph `interrupt()` 节点。
- `app/agent/aiops/executor.py`：把需审批调用保存为 `pending_tool_calls`，批准后执行原调用，拒绝后零执行。
- `app/services/aiops_service.py`：Executor 条件路由到 Approval Node，使用 `Command(resume=...)` 恢复。
- `POST /api/incidents/{incident_id}/approval`：提交批准或拒绝。

## 恢复语义

审批请求绑定 incident、身份、工具调用 ID、参数、风险和策略决策 ID。暂停时不消费计划，也不误发完成事件；恢复时不让 LLM 重新生成调用，而是执行 checkpoint 中已绑定的调用。测试用同一个 checkpointer 重建 `AIOpsService`，证明进程重启后仍能恢复。

## 面试表达

我实现的 HITL 不是同步弹窗，而是可持久化工作流中断：请求可跨进程等待，批准和拒绝都可审计，拒绝路径保证工具从未执行。
