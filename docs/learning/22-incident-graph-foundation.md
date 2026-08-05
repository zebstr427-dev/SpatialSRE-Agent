# 第 22 课：Incident Graph 基础

## 项目位置与功能

- `app/incident_graph/models.py`：服务、Pod、数据库、告警、变更、故障等节点及关系类型。
- `app/incident_graph/store.py`：项目自有存储接口语义与 NetworkX 实现。

图谱保存“谁依赖谁、谁被什么变更、哪个故障影响哪个服务”，补足文档向量检索难以表达的拓扑关系。节点/边使用 Pydantic 严格验证，可完整转为 JSON 并恢复。

## 设计亮点与边界

业务代码面向项目自有模型，不直接泄漏 NetworkX API，因此未来替换 Neo4j 时查询层契约可以保持。当前内存实现适合确定性测试和单机 Demo，不具备分布式并发、持久化和图数据库索引能力。

## 验收与秋招表达

`tests/unit/test_incident_graph.py` 验证端点完整性、节点边 round-trip 和非法关系拒绝。面试重点是“先定义领域图契约，再选择图存储”，而不是只说使用了 NetworkX。
