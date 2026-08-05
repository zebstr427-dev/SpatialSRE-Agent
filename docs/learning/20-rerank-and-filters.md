# 第 20 课：Rerank 与元数据过滤

## 项目位置与功能

`app/retrieval/hybrid.py` 在召回后执行确定性 Rerank，并在召回前按 service、fault type、version、source prefix 和时间范围过滤，最后稳定截取 TopK。`DocumentChunk` 保存来源和业务元数据，`RetrievalResult` 同时暴露 lexical/vector rank、融合分和 rerank 分。

## 关键设计

过滤必须早于排序，否则无权或无关文档会先占用候选名额。Rerank 只改变候选顺序，不制造新文档；并列时按 chunk ID 稳定排序，保证回放结果可重复。当前 reranker 是本地词项重合实现，接口允许替换 cross-encoder，但替换后必须重新跑检索评测。

## 验收与秋招表达

`tests/unit/test_hybrid_retrieval.py` 覆盖过滤组合、TopK、稳定顺序与 rerank。面试可表述为：我把召回、过滤、融合和精排拆成可替换阶段，并让每个阶段都能独立评测和降级。
