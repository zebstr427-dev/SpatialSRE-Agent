# 第 28 课：并行与失败隔离

## 项目位置与功能

`app/agent/enterprise_workflow.py` 从 RAG 同时分叉 SRE Agent 和 Change Agent，LangGraph 在 Root Cause 节点 fan-in。`AgentRoleRunner` 用 `asyncio.wait_for` 强制角色超时，将普通异常转换为结构化失败输出，并保留其他分支结果。

## 关键设计

并行分支通过 reducer 合并 evidence、role outputs 和 spans，不能同时覆盖同一普通字段。单个角色失败后流程生成 `completed_with_partial_results`，而不是丢弃已获得证据；超时与异常记录 error、latency 和 success=false。

取消信号不被普通 `Exception` 捕获，应用关闭仍可向上传播。当前重试不在角色 runner 内隐式发生，避免非幂等工具被重复调用；工具级有限重试仍由 Gateway 管理。

## 验收与秋招表达

`tests/unit/test_enterprise_workflow.py` 用 barrier 证明两分支确实并行，并覆盖超时、Change provider 异常和部分结果报告。
