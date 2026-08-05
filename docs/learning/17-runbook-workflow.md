# 第 17 课：Runbook 驱动工作流

## 项目位置与功能

- `app/agent/aiops/planner.py`：告警先匹配 Runbook，命中时不调用 LLM 自由规划。
- `app/agent/aiops/executor.py`：按结构化步骤选择工具并延续统一 Gateway、策略和审计链。
- `app/agent/aiops/state.py`：持久化 Runbook ID、版本和步骤。

Planner 的优先级是“确定性 Runbook -> 受控知识检索/LLM fallback”。这使常见故障采用稳定路径，未知故障仍有退化能力；执行失败或证据不足时，Replanner 可以补充步骤，但不能改变既有审计事实。

## 设计亮点与边界

Runbook 选择与工具执行分离：前者决定做什么，后者仍必须经过 Tool Gateway。这样 YAML 不能绕过身份、风险、Policy 和审批。当前 stop condition 作为流程数据保留，复杂条件解释器和发布审批属于后续平台化范围。

## 验收与秋招表达

`tests/unit/test_runbook_workflow.py` 验证命中时不调用 LLM、步骤顺序稳定，以及未知告警在依赖离线时仍能 fallback。面试重点是“用确定性流程约束 Agent，而不是完全依赖模型临场规划”。
