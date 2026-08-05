# 第 21 课：引用与检索评测

## 项目位置与功能

- `app/evals/retrieval.py`：Context Precision、Recall 与 citation coverage。
- `app/retrieval/hybrid.py`：稳定 `[doc:chunk_id]` 引用。
- `app/tools/knowledge_tool.py`：知识工具结果携带来源。
- `app/agent/evidence.py`：最终报告只保留真实 evidence ID，无证据时明确降级。

检索质量与生成质量分开测量：召回是否找对文档由 precision/recall 评价，回答是否引用已提供证据由 citation coverage 和 Guardrail 约束。稳定 ID 让同一数据集可以跨检索器和模型版本比较。

## 设计边界

引用存在不等于内容忠实，当前确定性指标不替代 faithfulness judge；它首先阻止“引用不存在来源”的基础错误。真实 RAGAS/judge 接入应保持可替换，并保存模型版本与评测输入。

## 验收与秋招表达

`tests/unit/test_retrieval_evaluation.py`、`test_knowledge_citations.py` 和 `test_evidence_guardrails.py` 共同覆盖指标、来源绑定、伪造引用清理与无证据降级。
