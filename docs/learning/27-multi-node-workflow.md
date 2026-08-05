# 第 27 课：LangGraph 多节点工作流

## 项目位置与功能

`app/agent/enterprise_workflow.py` 将企业诊断拆成 Triage、RAG、SRE、Change、Root Cause、Remediation、Report 节点。`EnterpriseState` 只传结构化字段：告警、Runbook、证据、变更、图上下文、根因、处置方案、角色输出和成本。

流程为：Triage -> RAG -> SRE/Change -> Root Cause -> Remediation -> Report。每个节点只更新自己负责的 state 片段，证据和角色输出通过 reducer 追加，最终结果可 JSON 序列化。

## 设计亮点与边界

节点间不靠大段自然语言互相传话，避免信息覆盖和难以评测。Root Cause 与 Report 分离，Report 只能组织已有证据。该工作流是结构化企业演示编排；现有 Durable Plan-Execute-Replan 仍负责 PostgreSQL checkpoint 与审批恢复。

## 验收与秋招表达

`tests/unit/test_enterprise_workflow.py` 验证节点汇合、结构化输出、输入防线和最终状态。面试重点是职责边界和共享状态设计，而不是简单宣称“用了多 Agent”。
