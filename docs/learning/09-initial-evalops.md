# 第 9 课：建立初始 EvalOps

完成日期：2026-08-04

对应范围：`feat(evalops): add deterministic tool-call evaluation`

## 企业问题

Agent 能运行并不等于每次都选择了正确工具。缺少固定评测集时，模型、提示词或工具注册发生变化后，即使接口仍返回成功，也可能出现漏调、多调、重复调用或错误工具选择，而且只能依靠人工观察发现。

本课建立离线、确定性的初始 EvalOps：使用版本化 JSONL 保存故障用例和标准工具轨迹，读取第 8 课定义的 `ToolCallAuditRecord`，计算工具选择和执行状态指标，并输出 JSON 报告。边界是它只验证评测机制和工具轨迹，不代表真实 LLM 已达到相同分数。

## 本课目标与完成结果

- 目标：建立 incident JSONL 用例、严格 schema、loader、确定性 runner、工具调用指标和报告。
- 实际完成：加入 3 条基线用例；校验未知字段、空值和重复 ID；使用多重集合计算 exact match、Precision、Recall 和 F1；单独计算工具成功率；报告可写入 UTF-8 JSON。
- 明确未覆盖：真实模型回放、工具参数准确率、根因命中率、报告忠实度、延迟、成本和数据集统计代表性。

## 设计与实现

```text
evals/incident_cases.jsonl
    -> load_incident_cases
        -> IncidentEvalCase[]
            -> injected CaseExecutor
                -> ToolCallAuditRecord[]
                    -> evaluate_case / run_evaluation
                        -> EvalReport -> JSON
```

`IncidentEvalCase` 使用 Pydantic `extra="forbid"` 阻止字段拼写错误被忽略，并使用冻结模型和元组保护标准答案。loader 逐行解析 UTF-8 JSONL，在错误中保留文件路径和行号，同时拒绝重复 `incident_id`。

runner 不直接依赖 LLM 或外部服务，而是接收注入的 `CaseExecutor`。工具匹配使用 `Counter` 多重集合交集，因此重复调用会降低 Precision，漏调会降低 Recall，顺序变化不会制造误报。工具选择指标与 `tool_success_rate` 分开，避免把外部工具超时误判为 Agent 决策错误。

## 为什么这样设计

- Pydantic 比手工读取字典更早暴露评测数据错误，也为后续扩展根因和报告指标提供稳定契约。
- 依赖注入让单元测试不访问 LLM、MCP、Milvus 或 PostgreSQL，结果可重复且容易定位回归来源。
- micro average 先汇总调用次数再计算总体指标，调用较多的用例会贡献更高权重，适合当前工具轨迹基线。
- JSON 报告保持平台无关，后续可由 CI、可视化页面或 Failure Replay 继续消费。

当前实现没有统计置信区间、数据集版本字段或阈值门禁，也没有验证工具参数和最终诊断内容。

## 验证证据

```powershell
.\.venv\Scripts\pytest.exe tests/unit/test_eval_loader.py tests/unit/test_eval_runner.py -q
.\.venv\Scripts\pytest.exe -m "not postgres" -q
.\.venv\Scripts\pytest.exe -m postgres -q
.\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\ruff.exe check $lesson9Files
.\.venv\Scripts\python.exe -m compileall -q app tests
git diff --check
```

实际结果：聚焦测试 `8 passed`，非 PostgreSQL 回归 `42 passed`，PostgreSQL 集成 `2 passed`，完整测试 `44 passed`；Ruff、compileall 和 diff 检查通过。

离线烟雾运行加载仓库中的 3 条基线用例，使用确定性 executor 生成第 8 课格式的工具审计记录，并在临时目录写入报告。实际输出为 `cases=3`、`exact_match_rate=1.00`、`tool_f1=1.00`、`tool_success_rate=1.00`、`report_written=True`；临时目录自动清理。

## 排错记录

首次加入仓库基线时，JSONL 被放入 `app/evals`，而测试约定的数据目录是项目根部的 `evals`，因此出现 `FileNotFoundError`。修正方式是区分 Python 评测程序与版本化评测数据：前者位于 `app/evals`，后者位于 `evals`。

报告 writer 首次收集测试时出现 `NameError: Path is not defined`。根因是函数类型标注和函数体使用了 `Path`，但模块导入区遗漏 `from pathlib import Path`。

Docker Desktop 关闭后，全量测试在导入 executor 时触发旧知识库代码的 Milvus 连接并失败。恢复 Docker、Milvus 和 PostgreSQL 后，非 PostgreSQL、PostgreSQL 和完整回归全部通过。这也暴露了旧模块存在导入期外部连接的技术债。

Ruff 最后报告 6 个 `W292`，原因是新增 Python 文件缺少末尾换行；定向修复第 9 课文件后静态检查通过。

## 常见错误

### 用普通集合计算工具准确率

集合会把重复调用合并。例如期望 `[A, B]`、实际 `[A, A]`，普通集合无法完整表达多调行为。多重集合按出现次数匹配，可以同时惩罚重复和遗漏。

### 混淆工具选择与工具执行成功

Agent 可能选对工具，但工具因网络或服务故障失败。选择指标和成功率必须分开，否则无法判断应优化决策逻辑还是基础设施。

### 把确定性满分当成真实模型成绩

本课烟雾运行的 executor 根据标准答案生成审计记录，满分只证明评测管道连通。真实模型质量必须由后续真实回放和更大评测集验证。

## 秋招知识点

- Agent EvalOps：不仅验证接口返回，还要对工具轨迹、根因、证据和报告建立可回归指标。
- 依赖注入：把非确定的模型执行与确定的指标计算分离，使失败能够定位到明确边界。
- Precision、Recall、F1：分别衡量乱调、漏调和二者平衡；多重集合保留调用次数语义。
- 数据契约：评测用例一旦进入 Git 和 CI，字段、ID 和指标含义就需要稳定版本管理。
- 分层验证：单元测试证明算法，完整回归证明兼容性，离线烟雾运行证明模块装配和报告输出。

## 面试问答

**问：你如何判断 Agent 升级后有没有发生工具选择退化？**

答：场景是模型或提示词升级后接口仍能成功，但可能漏调、多调或选错工具；风险是只靠人工 Demo 无法稳定发现回归。我把故障用例和标准工具轨迹保存为 JSONL，用 Pydantic 校验数据，通过注入 executor 获取结构化工具审计，再用多重集合计算 exact match、Precision、Recall 和 F1，并单独统计执行成功率。8 个聚焦测试、44 个完整测试和离线报告烟雾运行均通过。边界是当前仍未评估参数、根因和报告忠实度。

**问：为什么评测 runner 不直接调用真实 LLM？**

答：初始阶段首先要证明指标算法本身稳定。如果 runner 同时依赖真实模型和网络，测试失败时无法区分是指标错误、模型随机性还是基础设施故障。依赖注入先建立确定性回归层，真实模型回放在后续 Failure Replay 中加入。

## 下一课衔接

第 10 课进入 P1，建立 MCP Tool Gateway。第 8 课的工具审计和第 9 课的评测指标将用于验证统一路由、标准错误、超时和重试没有造成工具行为退化。
