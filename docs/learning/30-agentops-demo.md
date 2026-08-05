# 第 30 课：AgentOps 与企业级最终 Demo

## 项目位置与功能

- `app/observability.py`：OpenTelemetry span 与 checkpoint-safe AgentOps 记录。
- `app/agent/enterprise_workflow.py`：五角色调度、成本/延迟汇总、证据护栏和高风险处置建议。
- `app/api/aiops.py`：`POST /api/enterprise/incidents` 强类型入口与 Guardrail 错误映射。
- `app/demo.py`：完全确定性、无外部服务依赖的支付 CPU 故障演示。

每个角色生成 `agent.<role>` span，记录 incident/trace、成功状态、错误、模型、token、成本和延迟。最终 Demo 串联 CPU Runbook、Hybrid GraphRAG、支付到库存依赖、历史故障、发布/配置变更、根因、需要审批的回滚建议和 evidence-bound 报告。

## 企业边界

Demo 使用固定证据保证面试和 CI 稳定，不冒充实时生产数据；生产 handler 应替换为受 Identity、Policy、Gateway 和审批控制的真实 adapter。OpenTelemetry API 已接入，Exporter/Collector 地址属于部署配置。高风险 remediation 只生成审批要求，不在演示工作流中直接执行。

## 验收与秋招表达

`tests/unit/test_enterprise_demo.py` 验证完整根因、Runbook、两类变更评分、图上下文、至少三条证据、引用、审批标志和五个 spans；`test_aiops_api.py` 验证 API 装配、422 schema 和 400 Guardrail。命令行入口为：

```powershell
.\.venv\Scripts\python.exe -m app.demo
```

面试可完整表述为：我把可恢复 Runtime、安全工具面、Runbook/变更/检索/图谱能力与多角色工作流接成可观测、可回放、可评测的 Incident Response 平台，而不是彼此孤立的技术 Demo。
