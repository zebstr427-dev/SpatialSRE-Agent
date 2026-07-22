# SuperBizAgent Python 生产级升级规划增强版

> 基于原规划文档补充：新增 4 个模块，以及“到第二层为止”的项目内多 Agent 协作设计。本版不把 A2A 协议、Computer-use、代码 Agent 纳入当前主线。

## 项目定位

将 SuperBizAgent 从课程项目 / 功能 demo 升级为：

**面向企业 OnCall 场景的生产级 Incident Response Agent Platform**

核心卖点不是“做了 RAG 和 Agent”，而是：

> 实现一个可观测、可评测、可恢复、权限可控、支持 MCP 工具体系、故障知识图谱、Runbook-as-Code 和项目内多 Agent 协作的智能运维 Agent 平台。

## 源码现状判断

当前 Python 版已有 FastAPI、LangChain/LangGraph、Milvus、RAG、AIOps Plan-Execute-Replan、MCP Server 和静态前端，基础较完整，但仍偏 demo：

- `app/services/aiops_service.py` 已有 LangGraph `StateGraph`，实现 Planner -> Executor -> Replanner。
- `app/agent/aiops/state.py` 状态只有 `input / plan / past_steps / response`，还没有任务持久化、风险等级、证据链、审批状态、trace id。
- `app/tools/knowledge_tool.py` 的 RAG 目前是基础向量 topK 检索。
- `app/services/vector_index_service.py` 文档索引主要支持 `.txt/.md`。
- `mcp_servers/cls_server.py` 和 `mcp_servers/monitor_server.py` 已有 MCP 工具，但偏 mock，缺少统一网关、鉴权、审计、风险控制。
- `app/main.py` CORS 全开放，适合 demo，不适合生产叙事。

## 一、升级总架构

推荐升级为 7 层：

1. **数据接入层**

   接入运维文档、告警、日志、指标、K8s 事件、发布记录、工单、服务拓扑。

2. **知识与证据层**

   Milvus 保留做向量库，再加 PostgreSQL 存任务状态、评测集、审计记录；加 Neo4j 或轻量图存储做 Incident Graph。

3. **检索增强层**

   从基础 RAG 升级为 Hybrid RAG + Rerank + GraphRAG，支持全局故障模式总结和具体服务根因分析。

4. **Agent Runtime 层**

   继续使用 LangGraph，但把 `MemorySaver` 换成 PostgreSQL / SQLite 持久化 checkpointer，支持恢复、中断续跑、human-in-the-loop 和 fault tolerance。

5. **MCP Tool Gateway 层**

   将 Prometheus、CLS、K8s、Git、发布系统、工单系统统一注册成 MCP 工具。

6. **安全与审批层**

   为工具增加 risk level：只读工具自动执行，写操作 dry-run，高风险操作必须人工审批。

7. **EvalOps 与 Observability 层**

   Agent 每次运行都生成 trace、指标、评测结果，支持失败回放、工具调用日志、成本与延迟分析。

## 二、核心升级模块

### 1. Durable AIOps Agent Runtime

将当前 `PlanExecuteState` 扩展为：

```python
incident_id
trace_id
severity
plan
past_steps
evidence
tool_calls
risk_assessments
approval_requests
cost_metrics
response
status
```

目标：

- 支持任务恢复、重放、暂停审批、失败重试。
- 支持执行超时、最大步骤数、最大 token 成本控制。
- 支持每个 incident 的状态查询、历史回放和最终报告追踪。

面试亮点：

> 我不是简单调 LLM，而是实现了可恢复的长任务 Agent 执行引擎。

### 2. MCP Tool Gateway

将分散在 `cls_server.py`、`monitor_server.py` 里的工具升级为统一工具网关。

工具注册表字段：

```text
tool_name
schema
risk_level
owner
timeout
retry_policy
auth_scope
audit_enabled
```

执行链路：

```text
Agent -> Tool Router -> Policy Check -> MCP Client -> Tool Server -> Audit Log
```

工具风险等级：

- `READONLY`：查日志、查指标、查文档。
- `LOW_RISK_WRITE`：创建工单、发送通知。
- `HIGH_RISK_ACTION`：重启服务、扩容、回滚发布，必须审批。

面试亮点：

> 我基于 MCP 做了企业级工具治理，而不是只接了一个 MCP demo。

### 3. Incident Graph + GraphRAG

建图对象：

- 服务、接口、实例、Pod。
- 数据库、消息队列、缓存、下游依赖。
- 告警、日志错误码、发布版本、配置变更。
- 负责人、Runbook、历史 incident。

典型查询：

- 这个告警影响哪些下游服务？
- 最近 30 分钟是否有发布变更和错误日志同时出现？
- 历史上相似故障的根因是什么？

技术组合：

- Milvus：文档 chunk 向量检索。
- Neo4j / NetworkX：服务拓扑和故障关系图。
- GraphRAG：全局故障模式总结 + 局部实体追踪。

面试亮点：

> 普通 RAG 只能找文档，我的系统能沿服务依赖和变更链路做根因推理。

### 4. Hybrid RAG + Rerank + Query Rewrite

将当前 `retrieve_knowledge` 的基础 topK 向量检索升级为：

- Query Rewrite：把用户问题改写成运维检索 query。
- Hybrid Search：向量检索 + BM25 关键词检索。
- Rerank：对召回结果二次排序。
- Metadata Filter：按服务名、故障类型、文档版本、时间过滤。
- Citation：最终答案必须带证据来源。

面试亮点：

> 我对 RAG 做了可解释优化，并用评测集验证召回效果。

### 5. Agent EvalOps

建立 `evals/incident_cases.jsonl`：

每条 case 包含：

```json
{
  "incident_id": "case_cpu_001",
  "alert": "...",
  "metrics": "...",
  "logs": "...",
  "change_records": "...",
  "gold_root_cause": "...",
  "gold_actions": ["query_prometheus_alerts", "query_log", "query_change_record"],
  "expected_report_points": ["...", "..."]
}
```

评测指标：

- RAG：Context Precision、Context Recall、Faithfulness。
- Agent：Tool Call Accuracy、Tool Call F1、Agent Goal Accuracy。
- AIOps：根因命中率、误操作率、平均诊断时长、平均 token 成本。

建议实现：

- 使用 RAGAS + 自研 eval runner。
- OpenAI / 通义 / DeepSeek 只作为 judge model，可替换。
- 不绑定单一云厂商评测平台。

面试亮点：

> 我不是只让 Agent 跑通，而是建设了 Agent 回归评测体系。

### 6. OpenTelemetry GenAI Observability

记录关键 span：

```text
planner.generate_plan
retriever.search
reranker.rank
tool.call
replanner.decide
approval.wait
final_report.generate
```

每个 span 附带：

```text
model
tokens
latency
tool_name
tool_args
success
error
retrieved_docs
trace_id
incident_id
```

面试亮点：

> Agent 黑盒不可控，我做了全链路可观测和故障回放。

### 7. Guardrails + Human Approval

三类防线：

输入防线：

- 识别 prompt injection。
- 识别越权操作。
- 识别危险请求。

工具防线：

- 校验工具参数。
- 限制服务范围。
- 敏感操作进入审批。
- 高风险工具先 dry-run。

输出防线：

- 禁止编造证据。
- 报告必须引用真实工具结果。
- 没有证据时明确输出“不确定”或“无法判断”。

面试亮点：

> 我把 Agent 安全治理做到执行链路里，而不是只靠 prompt 约束。

### 8. Runbook-as-Code / Skill-as-Code

这是本版新增模块之一，适合 OnCall 项目作为强业务亮点。

目标：

将运维经验从自然语言文档升级为可执行、可版本化、可评测、可审计的 Runbook。

示例目录：

```text
runbooks/
  cpu_high_usage.yaml
  memory_leak.yaml
  service_unavailable.yaml
  slow_response.yaml
  disk_high_usage.yaml
```

每个 runbook 定义：

```yaml
id: cpu_high_usage
name: CPU high usage diagnosis
trigger:
  alert_name: HighCPUUsage
  severity: warning
steps:
  - id: query_alert
    tool: query_prometheus_alerts
    risk_level: READONLY
  - id: query_cpu_metrics
    tool: query_cpu_metrics
    risk_level: READONLY
  - id: query_logs
    tool: query_log
    risk_level: READONLY
stop_conditions:
  - no_active_alert
  - max_steps_reached
approval_required:
  - rollback_deployment
  - restart_service
expected_evidence:
  - cpu_usage_series
  - top_process
  - related_error_logs
```

落地方式：

- Planner 优先匹配 runbook，而不是完全让 LLM 自由规划。
- Executor 按 runbook 步骤执行工具。
- Replanner 可以在 runbook 失败或证据不足时补充步骤。
- Runbook 进入 git 版本管理，变更可 review。

面试亮点：

> 我把运维经验从文档沉淀为 Runbook-as-Code，让 Agent 的执行路径可控、可审计、可评测。

### 9. Change Intelligence / 变更关联分析

这是本版新增模块之一，也是 AIOps 根因定位里的高价值能力。

目标：

让 Agent 不只查日志和指标，还能主动关联“最近是否有发布、配置、依赖、扩缩容、数据库变更”。

建议接入数据：

- Git commit / merge request。
- CI/CD 发布记录。
- K8s Deployment rollout history。
- 配置中心变更记录。
- 镜像版本 diff。
- 数据库 migration 记录。

新增工具建议：

```text
query_recent_deployments(service_name, time_range)
query_config_changes(service_name, time_range)
query_git_commits(service_name, time_range)
query_k8s_rollout_history(namespace, deployment)
query_image_diff(old_image, new_image)
```

分析逻辑：

```text
告警时间窗口
-> 查询同时间段变更
-> 按服务、依赖、负责人、版本关联
-> 判断变更与异常是否同时间、同服务、同依赖链
-> 输出变更相关性置信度
```

面试亮点：

> AIOps 根因定位不能只查日志，我加入了变更关联分析，用发布、配置和拓扑信息提升根因命中率。

### 10. Agent Identity + Policy-as-Code

这是本版新增模块之一，用来强化企业级安全治理。

目标：

不仅工具有权限，Agent 自身也有身份、角色、可用工具范围和风险上限。

Agent Identity 示例：

```yaml
agent_id: sre_agent
role: sre_diagnosis
allowed_tools:
  - query_prometheus_alerts
  - query_log
  - query_k8s_events
allowed_services:
  - payment-service
  - order-service
max_risk_level: READONLY
approval_required: true
```

Policy-as-Code 示例：

```yaml
policies:
  - name: production_write_requires_approval
    when:
      environment: production
      risk_level: HIGH_RISK_ACTION
    action: require_human_approval

  - name: readonly_auto_allowed
    when:
      risk_level: READONLY
    action: allow

  - name: block_cross_service_action
    when:
      service_not_in_allowed_services: true
    action: deny
```

落地方式：

- MCP Tool Gateway 在执行前做 policy check。
- 高风险工具生成 approval request。
- 所有 deny / approval / execute 都进入 audit log。

面试亮点：

> 我给 Agent 建了身份和策略系统，解决企业落地时权限失控、误操作和不可追责的问题。

### 11. Failure Replay / Incident Simulator

这是本版新增模块之一，用来支撑 Agent 回归测试和 Demo 稳定性。

目标：

将历史故障和模拟故障做成可回放案例，每次改 prompt、改 RAG、改工具或改 runbook 后，都能验证 Agent 是否仍能稳定定位根因。

建议目录：

```text
incident_cases/
  cpu_high_usage/
    alert.json
    metrics.json
    logs.json
    changes.json
    expected.json
  memory_leak/
    alert.json
    metrics.json
    logs.json
    changes.json
    expected.json
```

回放流程：

```text
加载 case
-> mock MCP tools 返回固定证据
-> 执行 Agent workflow
-> 记录 trace
-> 对比 gold root cause、tool sequence、report points
-> 输出评测报告
```

评测输出：

```json
{
  "case_id": "cpu_high_usage",
  "root_cause_hit": true,
  "tool_call_accuracy": 0.86,
  "evidence_coverage": 0.91,
  "hallucination_found": false,
  "latency_ms": 18420,
  "token_cost": 0.034
}
```

面试亮点：

> 我支持故障案例回放，用于回归测试 Agent 的排障稳定性，而不是只靠一次演示证明系统可用。

### 12. 项目内多 Agent 协作设计

本版只做到第二层：项目内多 Agent。不引入 A2A 协议化跨系统协作。

#### 第一层：LangGraph 多节点 Workflow

这一层是必须落地的。它不强调“多 Agent 名词”，而是把当前 Planner -> Executor -> Replanner 升级为更清晰的任务型工作流。

建议节点：

```text
Triage Node
-> Plan Node
-> Evidence Collector Node
-> Root Cause Analyzer Node
-> Remediation Planner Node
-> Approval Node
-> Report Node
```

节点职责：

- `Triage Node`：解析告警类型、严重级别、影响服务、初始时间窗口。
- `Plan Node`：根据告警和 runbook 生成排查计划。
- `Evidence Collector Node`：调用 MCP 工具收集指标、日志、K8s 事件、发布记录。
- `Root Cause Analyzer Node`：结合证据、GraphRAG 和历史案例判断根因。
- `Remediation Planner Node`：生成处理建议、风险等级、dry-run 计划。
- `Approval Node`：对高风险动作生成人工审批请求。
- `Report Node`：生成诊断报告、证据链、复盘摘要。

共享状态：

```python
class IncidentState(TypedDict):
    incident_id: str
    trace_id: str
    alert: dict
    severity: str
    affected_services: list[str]
    runbook_id: str | None
    plan: list[dict]
    evidence: list[dict]
    change_records: list[dict]
    graph_context: dict
    root_cause: dict | None
    remediation: dict | None
    approval_requests: list[dict]
    report: str | None
    status: str
```

工程原则：

- 节点之间通过结构化 state 传递，不通过大段自然语言互相传话。
- 每个节点输出可被评测和回放。
- 每个工具调用都进入 evidence 和 audit log。

面试亮点：

> 我把 Agent 从简单对话循环升级成 LangGraph 任务工作流，每个节点职责清晰、状态可恢复、输出可评测。

#### 第二层：项目内多 Agent

这一层作为中期亮点。所有 Agent 仍运行在当前 Python 项目内，由 LangGraph 主图调度，不引入 A2A。

建议保留 5 个 Agent：

```text
Triage Agent：告警分流
RAG Agent：查 runbook 和历史案例
SRE Agent：查指标、日志、K8s
Change Agent：查发布和配置变更
Report Agent：生成诊断和复盘报告
```

各 Agent 职责：

1. **Triage Agent**

   输入：原始告警、用户请求。

   输出：

   ```text
   incident_type
   severity
   affected_service
   time_window
   suggested_runbook
   ```

2. **RAG Agent**

   输入：告警类型、服务名、用户问题。

   输出：

   ```text
   matched_runbooks
   historical_cases
   cited_docs
   confidence
   ```

3. **SRE Agent**

   输入：排查计划、服务名、时间窗口。

   输出：

   ```text
   metrics_evidence
   logs_evidence
   k8s_events
   anomaly_summary
   ```

4. **Change Agent**

   输入：服务名、时间窗口。

   输出：

   ```text
   deployments
   config_changes
   git_commits
   rollout_history
   change_correlation_score
   ```

5. **Report Agent**

   输入：所有 evidence、root cause、remediation、approval 状态。

   输出：

   ```text
   diagnosis_report
   evidence_table
   risk_assessment
   postmortem_summary
   ```

推荐调度方式：

```text
Triage Agent
-> RAG Agent
-> SRE Agent + Change Agent 并行
-> Root Cause Analyzer
-> Report Agent
```

并行策略：

- `SRE Agent` 和 `Change Agent` 可以并行执行。
- `RAG Agent` 的 runbook 结果作为 SRE Agent 的工具选择提示。
- `Report Agent` 只负责组织证据，不负责编造根因。

边界说明：

- 本阶段不做 A2A。
- 本阶段不做跨框架 Agent Mesh。
- 本阶段多 Agent 是项目内部角色分工，不是为了堆概念。

面试表达：

> MCP 解决 Agent 调工具的问题；项目内多 Agent 解决复杂故障处理中角色分工的问题。本阶段我没有盲目引入 A2A，而是先用 LangGraph 在单项目内实现可控、可评测的多 Agent 协作。

## 三、最终 Demo 剧本

“支付服务 CPU 100% 告警触发。Triage Agent 接收告警并判断为 `HighCPUUsage`，匹配 `cpu_high_usage.yaml` runbook。RAG Agent 检索相关 runbook 和历史相似案例。SRE Agent 通过 MCP 查询 Prometheus 指标、CLS 日志、K8s 事件。Change Agent 查询最近发布、配置变更和镜像版本 diff。Incident Graph 发现支付服务依赖库存服务，且 12 分钟前有一次灰度发布。GraphRAG 检索到历史相似故障，Root Cause Analyzer 判断根因为新版本批量任务导致线程池耗尽。系统给出置信度、证据链、影响面和处理建议。回滚属于高风险操作，进入人工审批。审批后执行 dry-run，再生成最终诊断报告和复盘文档，并把本次案例进入 Failure Replay 和评测集。”

这个 Demo 覆盖：

- Agentic Workflow。
- MCP Tool Gateway。
- Runbook-as-Code。
- Change Intelligence。
- 项目内多 Agent。
- GraphRAG。
- Human Approval。
- AgentOps。

## 四、落地优先级

### P0：生产级 Agent 骨架

预计 1-2 周：

- Durable Runtime：PostgreSQL / SQLite checkpointer。
- `IncidentState` 扩展。
- trace id / incident id。
- 工具调用审计。
- RAGAS + 自研 eval runner 初版。

### P1：企业可控执行

预计 2-3 周：

- MCP Tool Gateway。
- 工具风险分级。
- Agent Identity。
- Policy-as-Code。
- Human Approval。
- 输出证据链。

### P2：AIOps 根因能力增强

预计 3-4 周：

- Runbook-as-Code。
- Change Intelligence。
- Hybrid RAG。
- Rerank。
- Metadata filter。
- 引用来源。

### P3：高壁垒能力

预计 4-6 周：

- Incident Graph。
- GraphRAG。
- Failure Replay。
- LangGraph 多节点 workflow。
- 项目内多 Agent。

## 五、简历写法

可以写成：

“基于 FastAPI + LangGraph + MCP + Milvus 构建企业级智能 OnCall Agent 平台，支持 RAG 知识检索、告警诊断、日志/指标联动分析和故障报告生成。”

“设计 Durable Plan-Execute-Replan Runtime，将 Agent 执行状态持久化到数据库，支持中断恢复、失败重试、人工审批和执行审计。”

“实现 MCP Tool Gateway，统一接入 Prometheus、日志、K8s、发布系统等工具，并基于工具风险等级实现自动执行、dry-run 和 human-in-the-loop 审批。”

“引入 Runbook-as-Code，将 CPU 高负载、内存泄漏、服务不可用等运维经验沉淀为可执行、可版本化、可评测的诊断流程。”

“引入 Change Intelligence，将发布记录、配置变更、K8s rollout、Git commit 与告警时间线关联，提升根因定位准确率。”

“基于 LangGraph 设计项目内多 Agent 协作流程，将告警分流、知识检索、证据采集、变更分析和报告生成拆分为可观测、可评测的 Agent 节点。”

“建设 Agent EvalOps 体系，使用 RAGAS 和自研评测集评估 Context Precision、Faithfulness、Tool Call Accuracy、根因命中率和平均诊断耗时。”

## 六、参考技术源

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-03-26)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [OpenAI Guardrails and Human Review](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals)
- [OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/)
- [Microsoft GraphRAG](https://microsoft.github.io/graphrag/)
- [RAGAS Metrics](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/)
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
