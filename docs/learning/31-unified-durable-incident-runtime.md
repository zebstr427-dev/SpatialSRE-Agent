# 31 - 单一 Durable Incident Runtime 与双策略路由

## 为什么要合并

旧实现中 `AIOpsService` 与 `EnterpriseIncidentWorkflow` 分别编译和运行，导致企业
Agent 无法继承 PostgreSQL Checkpoint、公共审批和统一审计。v2 保留原有类名与节点
名，但生产环境只由 `AIOpsService` 编译一张 `StateGraph(IncidentState)`。

## 不变量

- `/api/chat` 仍是独立普通 RAG。
- `/api/aiops` 默认 `auto`；`/api/enterprise/incidents` 强制 `enterprise`。
- `planner/executor/replanner/approval` 名称不变，v1 checkpoint 缺失字段按 Simple 读取。
- Router 和证据评分是确定性代码，LLM 不决定安全关键路由。
- 所有外部工具调用经过每次调用隔离创建的 Tool Gateway；Provider 失败不伪造结果。
- `restart_service` 是 write 工具，production 要审批，且双层强制 `dry_run=true`。

## 路由规则

显式策略优先。Auto 遇到 critical、多服务、GraphRAG/变更关联要求，或 high 且存在
近期变更时直接 Enterprise；其他情况 Simple 优先。Simple 报告完成后按 Runbook、
证据来源、成功/失败工具调用和 citation 计算 `[0, 1]` 置信度，低于 `0.60`、无报告
或至少两个失败步骤时最多升级一次。

升级只清理未完成的 `plan/runbook_steps/pending_tool_calls/response`，保留 evidence、
past_steps、tool_calls、policy_decisions 与 routing_history，因此 Enterprise 可以复用已
完成事实，并且 Checkpoint 恢复不会重复执行已经结束的 Agent 节点。

## 面试追问

**为什么不总用多 Agent？** 多角色会增加 Provider 调用、延迟和成本；简单单服务故障
先走 Planner–Executor 更经济，证据不足再升级。

**为什么 Router 不用 LLM？** severity、服务数、变更标志都是结构化事实；确定性规则
可测试、可审计，也避免提示词影响安全关键流程。

**单 Provider 挂了怎么办？** 对应角色写 `provider_failures`，其他并行角色继续，最终
状态为 `completed_with_partial_results`，报告不得把缺失数据包装成事实。

**企业 Agent 是否“运行在 AIOps 上”？** v2 可以这样表述：它们是同一 Durable
Incident Runtime 中的 Enterprise 节点组，共享父图状态与执行边界，而不是第二套服务。
