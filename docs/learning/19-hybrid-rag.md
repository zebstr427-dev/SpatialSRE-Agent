# 第 19 课：Query Rewrite 与 Hybrid RAG

## 项目位置与功能

- `app/retrieval/hybrid.py`：确定性 Query Rewrite、BM25、向量适配器和 Reciprocal Rank Fusion。
- `tests/unit/test_hybrid_retrieval.py`：关键词、向量、融合排序及向量后端失败降级。

查询会补充 service、fault type、incident、diagnosis 等领域词，再并行形成关键词排名和向量排名。RRF 只依赖名次而非不同后端不可直接比较的原始分数，因此可以稳定融合；向量服务异常时仍保留 BM25 结果。

## 设计亮点与边界

检索核心不绑定 Milvus，向量搜索通过 callable adapter 注入。这样单元测试无需外部服务，生产仍可连接现有 Milvus。确定性 rewrite 便于回归，但不覆盖复杂同义词和多轮消歧，后续可替换为受评测约束的模型 rewrite。

## 秋招表达

不要只说“向量加关键词”。应说明异构分数为何不能直接相加、RRF 如何稳定融合，以及向量后端故障时如何保持最小可用检索。
