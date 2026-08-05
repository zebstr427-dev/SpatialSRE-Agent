# 第 29 课：项目内多 Agent 角色

## 项目位置与功能

`RoleOutput` 定义每个角色统一 I/O：role、status、summary、结构化 data、evidence、起止时间、延迟和 error。`build_default_agents()` 注册 Triage、RAG、SRE、Change、Report 五个角色，`EnterpriseIncidentWorkflow` 在构造时拒绝缺失角色。

## 五个角色

- Triage：识别服务、严重级别、故障类型和时间窗。
- RAG：匹配 Runbook，执行 Hybrid GraphRAG，返回引用。
- SRE：提供指标、日志与根因线索。
- Change：查询版本化变更仓库并计算相关性。
- Report：只组织 root cause、remediation 和 evidence。

## 设计亮点与边界

角色是项目内职责隔离，不是跨系统 A2A；runner 可注入 handler，测试无需 LLM 和外部服务。角色输出被冻结并序列化后写入 state，便于回放和单角色评测。当前默认 handler 是确定性演示 adapter，生产接入外部工具仍必须经过 Gateway。

## 验收与秋招表达

测试覆盖角色注册、输出序列化、隔离失败和五角色 AgentOps spans。面试时强调 MCP 解决“如何调工具”，角色协作解决“复杂任务如何分工”。
