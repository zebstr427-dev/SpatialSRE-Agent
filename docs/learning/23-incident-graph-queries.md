# 第 23 课：Incident Graph 查询

## 项目位置与功能

`app/incident_graph/queries.py` 提供依赖多跳遍历、受影响上游、时间窗变更关联和历史相似故障查询；`app/incident_graph/store.py` 提供有向边、反向边和限定跳数邻域能力。

这些查询直接回答 OnCall 的四个关键问题：依赖谁、故障会影响谁、告警附近改了什么、过去是否出现同类错误。遍历维护 `seen` 集并限制深度，避免循环依赖导致无限搜索。

## 设计亮点与边界

影响分析使用反向依赖，依赖分析使用正向依赖，两者不能混用。相似故障当前按稳定错误码匹配，是可解释基线；生产可叠加 embedding 或 learned similarity，但必须保留来源和阈值。

## 验收与秋招表达

`tests/unit/test_incident_graph.py` 用多层服务拓扑、变更时间窗和两个历史 incident 验证四类查询。面试时应能解释边方向、最大深度和环检测。
