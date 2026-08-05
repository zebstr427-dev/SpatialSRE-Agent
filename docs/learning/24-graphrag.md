# 第 24 课：GraphRAG

## 项目位置与功能

- `app/incident_graph/graphrag.py`：实体 seed、限定跳数局部子图、全局统计、文档融合和 provenance citation。
- `app/agent/enterprise_workflow.py`：RAG Agent 把图上下文转成共享状态和可引用 evidence。

GraphRAG 先从问题命中服务/变更/历史故障实体，再扩展邻域；全局摘要保留整个图的节点和边类型分布。文档部分可注入 Hybrid Retriever，真实复用 Query Rewrite、BM25/向量融合和 Rerank；最终 citation 同时区分 `[graph:*]` 与 `[doc:*]`。

## 设计亮点与边界

局部图用于具体根因链，全局统计用于故障模式背景，两类上下文不混成不可追踪的大文本。当前实体识别为确定性 token 匹配，适合回归；生产可换 NER/实体链接，但必须保留 seed 和路径 provenance。

## 验收与秋招表达

`tests/unit/test_graphrag.py` 覆盖邻域、全局摘要、引用，以及无关键词时仅靠向量命中的 Hybrid 路径。最终 Demo 验证 payment、inventory、历史 incident 同时进入报告证据。
