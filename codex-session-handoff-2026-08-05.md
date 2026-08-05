# Codex 会话交接文件

> 用途：把当前会话的目标、已完成工作、代码结论和产物交接给另一台电脑上的 Codex。
>
> 新 Codex 不需要从头猜测项目结构。请先完整阅读本文件，再按“继续会话提示词”工作。

## 1. 当前项目

- 项目名称：SuperBizAgent Python
- 当前项目目录：`C:\zyh\OnCallAgent\Python-super_biz_agent_py-release-2026-05-17\super_biz_agent_py-release-2026-05-17`
- 项目在新电脑上的绝对路径可以不同，以下文件位置均以项目根目录为基准。
- 改造依据：`python-agent-upgrade-plan-2026-enhanced.md`
- 用户确认状态：升级计划规定的 P0-P3 Python 改造已经完成并验收。

## 2. 用户的核心要求

用户希望以资深软件架构师视角，基于实际代码说明整个项目：

- 项目解决什么问题、谁在使用、如何运行。
- 应用入口、启动流程和初始化过程。
- 前端、API、业务服务、工作流、数据访问和基础设施的职责。
- 模块之间的调用关系、信息流、依赖方向和系统边界。
- PostgreSQL、Milvus、文件、内存状态和外部 API 的作用。
- 测试、构建、部署和运维相关内容。
- 所有结论必须以实际代码为依据，不能只根据 README、目录名或升级计划推断。
- 使用 Mermaid `flowchart`，不要画成目录树。
- 原始大图过于复杂，因此最终采用“1 张总览图 + 4 张子图”。
- 说明必须使用中文大白话，并且由浅入深。
- 最终报告要转换为 PDF。

## 3. 本会话已经完成的工作

1. 完整阅读了升级计划、README、依赖、应用入口、API、服务、工作流、前端、基础设施、测试、部署和 P0-P3 相关实现。
2. 确认 `C:\zyh\OnCallAgent` 下实际分析的 Git 仓库是当前 Python 项目；同级 Java 和 Go 目录是独立参考项目。
3. 形成了分层架构结论，并输出过可渲染的 Mermaid 总览图和子图。
4. 根据用户反馈，把单张复杂图拆为：
   - 系统总览。
   - 普通聊天与知识入库。
   - 持久化 AIOps 诊断。
   - 企业多智能体事故分析。
   - 启动、存储与运行边界。
5. 生成了 12 页中文 PDF，逐页检查了中文、图形、表格、页码和横竖版布局。
6. 重新运行过不依赖 PostgreSQL 的测试：`115 passed`，覆盖率 `64.18%`。
7. 没有修改业务代码。

## 4. 已生成产物

最终 PDF：

`output/pdf/super-biz-agent-architecture-report.pdf`

PDF 包含：

- 项目定位。
- 1 张系统总览图。
- 4 张专题子图。
- 5 条核心调用链。
- 三种业务路径的差异表。
- 完整模块职责表。
- 架构说明、重点耦合、代码依据和待确认事项。

PDF 生成时使用的中间文件位于：

`tmp/pdfs/oncall-architecture/`

该目录只是渲染和检查用，不属于业务代码，也不是继续分析所必需的内容。

## 5. 项目定位

这是一个面向值班运维人员的 AI 运维助手。它解决的核心问题是：告警出现以后，如何查询知识、日志、指标和变更信息，收集可信证据，分析可能根因，并形成处置建议或事故报告。

系统同时存在三条不同的业务路径：

1. 普通 AI 对话和知识库问答。
2. 可暂停、可审批、可恢复的持久化 AIOps 诊断。
3. 按固定角色协作的企业多智能体事故分析。

核心技术栈：FastAPI、Uvicorn、LangChain、LangGraph、Qwen/DashScope、PostgreSQL、Milvus、NetworkX、原生 HTML/CSS/JavaScript。

## 6. 最重要的架构结论

### 6.1 应用入口与启动

- `app/run.py` 负责启动 Uvicorn。
- `app/main.py` 创建 FastAPI 应用、挂载静态页面并注册路由。
- FastAPI `lifespan` 启动时连接 Milvus。
- `lifespan` 同时打开 PostgreSQL 连接池并创建 LangGraph PostgreSQL Saver。
- 启动阶段创建 `AIOpsService` 和 `EnterpriseIncidentWorkflow`，放入 `app.state`。
- 应用退出时关闭 PostgreSQL 连接池和 Milvus 连接。

### 6.2 三条业务路径

#### 普通聊天

入口：

- `POST /api/chat`
- `POST /api/chat_stream`
- `GET /api/chat/session/{session_id}`
- `POST /api/chat/clear`

主要实现：

- `app/api/chat.py`
- `app/services/rag_agent_service.py`

状态与工具：

- 后端使用 LangGraph `MemorySaver` 保存当前进程中的会话。
- 浏览器使用 `localStorage` 保存前端聊天列表，最多 50 条。
- Chat Agent 直接绑定默认本地工具和 MCP 工具。
- Chat Agent 没有经过 `ToolGateway` 的身份、风险、审批和审计控制。
- 服务重启后，后端 MemorySaver 会话不会保留。

#### 持久化 AIOps

入口：

- `POST /api/aiops`
- `GET /api/incidents/{incident_id}`
- `POST /api/incidents/{incident_id}/approval`

主要实现：

- `app/api/aiops.py`
- `app/services/aiops_service.py`
- `app/agent/aiops/`
- `app/agent/approval.py`
- `app/agent/tool_gateway.py`

工作流：

`Planner -> Executor -> Approval 或 Replanner -> Executor 或结束`

关键规则：

- `Planner` 制定诊断计划。
- `Executor` 执行当前步骤并收集结果。
- 如果产生待审批工具调用，则进入 `Approval Node`。
- `Approval Node` 使用 LangGraph interrupt 暂停。
- 值班人员调用审批 API 后，通过 `Command(resume=...)` 恢复。
- `Replanner` 判断是否继续执行、调整计划或形成最终报告。
- `incident_id` 同时作为 LangGraph `thread_id`，用于从 PostgreSQL 找回事故状态。
- `trace_id` 标识一次执行链路，不等同于事故长期编号。
- API 使用 SSE 返回 plan、step、approval、complete 和 error 等事件。

#### 企业多智能体工作流

入口：

- `POST /api/enterprise/incidents`

主要实现：

- `app/agent/enterprise_workflow.py`
- `app/retrieval/hybrid.py`
- `app/incident_graph/`
- `app/runbooks.py`
- `app/change_intelligence.py`

固定流程：

`Triage -> RAG -> SRE 与 Change 并行 -> Root Cause -> Remediation -> Report`

当前边界：

- 工作流是确定性的结构化流程，不是多个 Agent 自由讨论。
- 默认角色运行器包含固定或演示性质的数据。
- Incident Graph 使用进程内 NetworkX。
- 企业工作流没有接入 PostgreSQL checkpointer，不能像持久化 AIOps 一样跨重启恢复。
- 当前网页没有调用该接口，只能由外部 API 调用方使用。

## 7. 数据与基础设施

### PostgreSQL

- 只用于持久化 AIOps 的 LangGraph 检查点。
- 连接和 Saver 生命周期在 `app/core/checkpoint.py`。
- 使用 `AsyncPostgresSaver` 和安全序列化配置。

### Milvus

- 保存知识文档向量，Collection 名称是 `biz`。
- 向量维度为 1024。
- 文件上传后经过切分、DashScope Embedding，再写入 Milvus。
- 普通知识工具从 Milvus 执行 Top-K 相似度检索。
- 相关实现：`app/core/milvus_client.py`、`app/services/vector_*`。

### 本地文件

- `uploads/`：用户上传的 txt、md 文件。
- Runbook：YAML/JSON 文件。
- Change Intelligence：JSONL 数据。
- 策略、评测和 replay 案例也主要使用 YAML/JSON/JSONL。

### 内存状态

- 普通聊天：LangGraph `MemorySaver`。
- Incident Graph：NetworkX 内存图。
- 这两类状态都不是跨进程持久化存储。

### 外部系统

- DashScope/Qwen：聊天、规划、推理和向量化。
- MCP 服务：配置地址默认为 8003 和 8004，主要面向日志和监控工具。
- Prometheus：默认地址为 9090，用于指标查询。

### 当前没有的基础设施

代码中没有发现 Redis、Kafka、RabbitMQ 或其他消息队列/缓存系统。SSE 和并行执行属于 HTTP 流式返回及进程内异步处理，不是消息队列。

## 8. 知识入库信息流

`浏览器上传文件 -> app/api/file.py -> uploads/ -> 文档切分 -> DashScope Embedding -> VectorIndexService -> Milvus biz collection`

相关文件：

- `app/api/file.py`
- `app/services/document_splitter_service.py`
- `app/services/vector_embedding_service.py`
- `app/services/vector_index_service.py`
- `app/services/vector_search_service.py`
- `app/services/vector_store_manager.py`

上传接口只允许 txt 和 md，单文件上限 10 MB。向量索引失败时，当前代码仍可能把上传本身返回为成功，只记录索引错误日志。

## 9. Tool Gateway 的职责

`app/agent/tool_gateway.py` 是持久化 AIOps 的受控工具执行边界，负责：

- 工具注册与来源标记，区分 local 与 MCP。
- Agent 身份允许的工具范围。
- 服务范围和风险上限。
- 风险分类：只读、写操作、高风险。
- Policy-as-Code：允许、拒绝或要求审批。
- 写操作 dry-run 要求。
- 超时、重试和错误标准化。
- 审计回调。
- 与证据结构结合记录工具结果来源。

普通 Chat Agent 当前绕过该边界，这是后续安全治理最需要关注的差异。

## 10. 前端现状

- 前端位于 `static/index.html`、`static/app.js`、`static/styles.css`。
- 使用原生 JavaScript，没有专门的状态管理库和请求层框架。
- 页面支持普通聊天、流式聊天、文件上传和 `/api/aiops`。
- 页面没有持久化 AIOps 人工审批界面。
- 页面没有企业多智能体接口入口。
- 浏览器历史保存在 `localStorage`，后端历史来自 MemorySaver，二者可能不完全一致。

## 11. 架构分层说明

项目不是严格的 `Controller -> Service -> Repository` 架构：

- `app/api` 相当于 Controller。
- `app/services` 和 `app/agent` 共同承担业务层和工作流编排。
- `app/core/checkpoint.py`、`app/core/milvus_client.py`、`vector_store_manager.py` 相当于数据访问层。
- `app/models` 主要是 API 与状态数据模型。
- 当前没有统一 Repository 接口。

正常依赖方向：

`浏览器或外部调用方 -> FastAPI 路由 -> Service/Workflow -> 工具与检索 -> 数据库或外部系统`

## 12. 重点风险与耦合

1. 普通 Chat Agent 绕过 Tool Gateway。
2. 前端 localStorage 与后端 MemorySaver 是两份会话状态，可能不同步。
3. `VectorStoreManager` 全局实例可能在模块导入阶段连接 Milvus，增加启动和测试耦合。
4. 企业工作流默认图数据和部分角色证据带有演示性质。
5. 企业工作流与普通 Chat 都不是 PostgreSQL 持久化流程。
6. 前端缺少审批和企业工作流入口。
7. `start-windows.bat` 和 Makefile 没有统一启动 `compose.postgres.yml`。
8. OpenTelemetry 已有 Span，但未发现 exporter 或 collector 配置。

## 13. 已确认与待确认

### 已从代码确认

- FastAPI 的入口和生命周期。
- 三条业务路径及其状态差异。
- AIOps LangGraph 节点和审批恢复关系。
- Tool Gateway 的身份、风险、策略和 dry-run 控制。
- PostgreSQL 与 Milvus 的职责边界。
- 前端实际调用的接口。
- NetworkX、文件数据和 MemorySaver 的内存/本地边界。
- 当前没有 Redis 和消息队列。

### 待确认

- 生产环境实际部署在 Kubernetes、虚拟机还是其他云平台。
- 生产 MCP 服务实际提供的日志范围、监控范围和权限。
- OpenTelemetry 最终向哪里发送数据。
- PostgreSQL 的生产备份、高可用和灾难恢复策略。
- 人工审批是否计划由其他系统而不是当前网页实现。

## 14. 关键参考文件

- `python-agent-upgrade-plan-2026-enhanced.md`
- `README.md`
- `docs/learning/README.md`
- `requirements.txt`
- `app/main.py`
- `app/run.py`
- `app/api/aiops.py`
- `app/api/chat.py`
- `app/api/file.py`
- `app/api/health.py`
- `app/services/aiops_service.py`
- `app/services/rag_agent_service.py`
- `app/agent/aiops/state.py`
- `app/agent/tool_gateway.py`
- `app/agent/identity.py`
- `app/agent/policy.py`
- `app/agent/approval.py`
- `app/agent/evidence.py`
- `app/agent/enterprise_workflow.py`
- `app/retrieval/hybrid.py`
- `app/incident_graph/`
- `app/runbooks.py`
- `app/change_intelligence.py`
- `app/core/checkpoint.py`
- `app/core/milvus_client.py`
- `static/app.js`
- `compose.postgres.yml`
- `vector-database.yml`
- `tests/`
- `app/evals/`
- `app/replay/`

## 15. 会话过程摘要

1. 用户最初要求深入分析项目并输出完整结构图，要求结论全部来自实际代码。
2. 用户补充说明 P0-P3 改造已经完成并验收，要求重新生成。
3. 完成代码阅读后，最初输出了一张较大的 Mermaid 总览图。
4. 用户认为图太大太乱，要求拆成一张大图和几个子图，并给出详细说明。
5. 用户进一步要求使用大白话、由浅入深地解释。
6. 最终形成 1 张总览图和 4 张子图，并补充核心调用链、职责表、架构说明和不确定项。
7. 用户要求把最终内容转换成 PDF。
8. 已生成并检查 `output/pdf/super-biz-agent-architecture-report.pdf`。
9. 用户现在要求把会话保存成文件，以便另一台电脑上的 Codex 继续。

## 16. 新电脑继续时的建议

把整个项目目录同步到新电脑后，在 Codex 中打开项目根目录，然后发送以下提示词：

```text
请先完整阅读 codex-session-handoff-2026-08-05.md、
python-agent-upgrade-plan-2026-enhanced.md 和当前代码。

这是上一个 Codex 会话的交接文件。请继承其中已经确认的架构结论，
不要只根据目录名或 README 重新猜测，也不要无理由重复已经完成的分析。

先告诉我你已经理解的当前状态，然后继续处理我的下一条要求。
输出使用中文大白话，由浅入深；所有新结论仍需以实际代码为依据。
```

如果新电脑只拿到本文件，没有完整项目代码，新 Codex只能理解历史结论，不能继续进行可靠的代码修改或验证。因此应同步整个 Git 仓库，至少同时包含升级计划、代码、测试和最终 PDF。
