# OnCall Agent P0-P3 学习路线

这一组课程完成 P0-P3 全路线。目标不只是让 Demo 使用 PostgreSQL，而是建立一套可解释、可测试、可恢复、权限可控，并具备 Runbook、变更关联、混合检索、故障图谱、回放和项目内多 Agent 协作的 Incident Response Agent Platform。

## 架构主线

```text
HTTP / SSE
    -> FastAPI lifespan
        -> CheckpointRuntime
            -> AsyncConnectionPool
                -> AsyncPostgresSaver
                    -> AIOpsService
                        -> LangGraph StateGraph

incident_id -> LangGraph thread_id -> PostgreSQL checkpoints
trace_id    -> 一次执行链路
session_id  -> 用户会话，不再承担故障隔离职责

EnterpriseIncidentWorkflow
    -> Triage Agent
    -> RAG Agent (Runbook + Hybrid RAG + GraphRAG)
    -> SRE Agent || Change Agent
    -> Root Cause -> Remediation -> Report
        -> evidence citations + AgentOps spans
```

## 课程目录

0. [冻结可运行基线](00-baseline.md)
1. [建立 pytest 测试基线](01-pytest-baseline.md)
2. [受控升级 Agent 依赖](02-dependency-upgrade.md)
3. [用 TDD 设计 IncidentState](03-incident-state.md)
4. [建立 PostgreSQL 基础设施](04-postgres-infrastructure.md)
5. [实现 Checkpointer 生命周期](05-checkpointer-lifecycle.md)
6. [接入 Durable AIOps API](06-durable-aiops-api.md)
7. [证明跨进程恢复](07-recovery-proof.md)
8. [持久化工具调用审计](08-tool-call-audit.md)
9. [建立初始 EvalOps](09-initial-evalops.md)
10. [建立 MCP Tool Gateway](10-mcp-tool-gateway.md)
11. [风险等级与 Dry-run](11-risk-and-dry-run.md)
12. [Agent Identity](12-agent-identity.md)
13. [Policy-as-Code](13-policy-as-code.md)
14. [可恢复的人类审批](14-human-approval.md)
15. [证据链与 Guardrails](15-evidence-and-guardrails.md)
16. [Runbook-as-Code 基础](16-runbook-foundation.md)
17. [Runbook 驱动工作流](17-runbook-workflow.md)
18. [Change Intelligence](18-change-intelligence.md)
19. [Query Rewrite 与 Hybrid RAG](19-hybrid-rag.md)
20. [Rerank 与元数据过滤](20-rerank-and-filters.md)
21. [引用与检索评测](21-retrieval-evaluation.md)
22. [Incident Graph 基础](22-incident-graph-foundation.md)
23. [Incident Graph 查询](23-incident-graph-queries.md)
24. [GraphRAG](24-graphrag.md)
25. [Failure Replay 基础](25-failure-replay.md)
26. [Replay 指标与报告](26-replay-metrics.md)
27. [LangGraph 多节点工作流](27-multi-node-workflow.md)
28. [并行与失败隔离](28-parallel-failure-isolation.md)
29. [项目内多 Agent 角色](29-agent-roles.md)
30. [AgentOps 与企业级最终 Demo](30-agentops-demo.md)

## 最终验证命令

```powershell
# 不依赖外部服务的测试
.\.venv\Scripts\pytest.exe -m "not postgres" -q

# 只运行真实 PostgreSQL 集成测试
.\.venv\Scripts\pytest.exe -m postgres -q

# 静态检查和语法检查
$changedPython = git diff --name-only 4d2a903..HEAD -- "*.py"
.\.venv\Scripts\ruff.exe check $changedPython
.\.venv\Scripts\python.exe -m compileall -q app tests

# 确定性企业级演示
.\.venv\Scripts\python.exe -m app.demo
```

P0-P3 最终验收结果（2026-08-05）：非 PostgreSQL `115 passed`，真实 PostgreSQL `2 passed`，完整套件 `117 passed`，应用代码总覆盖率 `64.34%`。

## 已知基线技术债

`ruff check app tests` 仍会报告旧 RAG、MCP 和向量服务中的 165 条风格问题。本阶段所有新增和修改的 Python 文件已通过 Ruff；遗留告警没有通过无关的大规模格式化混入本阶段提交，后续应单独建立 lint-baseline 治理任务。

## 面试叙事

不要只说“把 MemorySaver 换成 PostgreSQL”。完整表达应是：

> 我把进程内 Agent Demo 重构为由 FastAPI lifespan 管理的 durable runtime。每个 incident 映射为独立 LangGraph thread，checkpoint 通过 Psycopg 异步连接池持久化；我用确定性节点证明工作流能跨连接池恢复，且恢复不会重跑已完成节点。单元测试完全隔离 LLM、MCP、Milvus 和 PostgreSQL，真实数据库行为由独立 marker 的集成测试验证。

工具执行层进一步保存 checkpoint-safe 的结构化审计记录，使用调用 ID 关联请求与实际工具结果，并覆盖成功、工具错误和执行异常。真实运行时已经证明这些记录可从 incident API 查询并跨 PostgreSQL 连接池恢复。

P0 最后建立了确定性 EvalOps：版本化 JSONL 保存故障用例和标准工具轨迹，Pydantic 在加载边界验证数据，runner 使用多重集合计算工具调用 Precision、Recall 和 F1，并把工具选择与执行成功率分开统计。该层为 P1 的 Tool Gateway、风险控制和审批回归提供统一质量基线。

P1 首先建立统一 Tool Gateway：本地与 MCP 工具进入同一注册表，Executor 通过标准执行结果处理找不到、超时和工具异常，并把结果接入已有审计链。重试能力保持显式且有界，默认单次尝试，为后续风险等级、dry-run、身份和策略控制提供唯一执行入口。

P1 随后把风险、身份、Policy-as-Code、人类审批和证据护栏叠加到同一执行边界。未知工具默认高风险，写操作被强制 dry-run；身份限制工具、服务和风险上限；策略决策和审批请求随 checkpoint 持久化；最终报告只能引用真实成功工具产生的 evidence，无证据时明确降级。

P2 将运维经验沉淀为五类版本化 Runbook，并让 Planner 优先走确定性流程；Change Intelligence 将发布、配置、Git 和 K8s 变更按服务、依赖、时间和环境评分；Hybrid RAG 组合 Query Rewrite、BM25、向量 RRF、Rerank、元数据过滤和稳定引用，并用独立指标验证检索质量。

P3 用项目自有图模型和 NetworkX 建立 Incident Graph，支持依赖、影响、变更和相似故障查询；GraphRAG 将局部子图、全局摘要和 Hybrid 文档融合为带 provenance 的上下文；Failure Replay 用隔离 fixture 回归根因、工具轨迹、证据、幻觉、延迟和成本。最终 LangGraph 工作流编排五个项目内 Agent，SRE/Change 并行且失败隔离，每个角色生成 OpenTelemetry/AgentOps 记录，并通过强类型 API 和确定性 Demo 展示完整链路。
