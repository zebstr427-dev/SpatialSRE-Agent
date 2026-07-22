# PostgreSQL Durable Agent Runtime 学习路线

这一组课程对应 `feature/postgres-durable-runtime` 分支。目标不只是让 Demo 使用 PostgreSQL，而是建立一套可解释、可测试、可恢复的 Agent Runtime。

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
```

完整测试应为 `31 passed`，其中 PostgreSQL 集成测试应为 `2 passed`。

## 已知基线技术债

`ruff check app tests` 仍会报告旧 RAG、MCP 和向量服务中的 165 条风格问题。本阶段所有新增和修改的 Python 文件已通过 Ruff；遗留告警没有通过无关的大规模格式化混入本阶段提交，后续应单独建立 lint-baseline 治理任务。

## 面试叙事

不要只说“把 MemorySaver 换成 PostgreSQL”。完整表达应是：

> 我把进程内 Agent Demo 重构为由 FastAPI lifespan 管理的 durable runtime。每个 incident 映射为独立 LangGraph thread，checkpoint 通过 Psycopg 异步连接池持久化；我用确定性节点证明工作流能跨连接池恢复，且恢复不会重跑已完成节点。单元测试完全隔离 LLM、MCP、Milvus 和 PostgreSQL，真实数据库行为由独立 marker 的集成测试验证。
