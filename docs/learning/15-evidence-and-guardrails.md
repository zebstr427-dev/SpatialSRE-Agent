# 第 15 课：证据链与 Guardrails

## 实现位置与功能

- `app/agent/evidence.py`：输入约束、工具证据 provenance、报告引用绑定和无证据降级。
- `app/agent/aiops/executor.py`：只有成功的 Gateway 结果才能生成 evidence。
- `app/agent/aiops/replanner.py`：最终报告绑定真实 evidence ID。
- `app/services/aiops_service.py`：完成事件返回 evidence 和 citations，incident API 返回完整持久化证据。

## 安全边界

输入侧拒绝空输入、超长内容和确定性 prompt injection 模式。证据记录包含工具调用 ID、参数、执行身份、风险、dry-run、策略决策和时间。输出侧移除不存在的 citation；无证据时丢弃模型的根因断言，固定输出“证据不足”。

## 验收与面试表达

测试覆盖 provenance 序列化、来源分类、伪造引用清理、无证据降级、输入注入和 Executor 证据生成。P1 完整非 PostgreSQL 回归为 `80 passed`。面试可以表述为：报告可信度由真实工具结果和稳定引用建立，模型无法凭文本自行制造证据。
