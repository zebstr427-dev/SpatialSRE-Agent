# 第 18 课：Change Intelligence

## 项目位置与功能

- `app/change_intelligence.py`：变更模型、JSONL 仓库、时间窗查询和可解释评分。
- `app/tools/change_tools.py`：发布、配置、Git、K8s rollout 查询工具。
- `data/change_records.jsonl`：版本化演示数据。
- `app/agent/enterprise_workflow.py`：Change Agent 将相关变更写入共享状态和证据链。

相关性由同服务/依赖服务、时间距离和环境一致性组成，输出 `score`、`reasons` 和 `time_delta_seconds`。最终工作流同时保留配置变更和版本发布，并只用字段完整的版本发布增强 rollout 根因描述。

## 设计亮点与边界

评分是可解释规则，不把“时间接近”直接当作因果。JSONL repository 是供应商无关的端口，后续可替换 CI/CD、Git 或配置中心 adapter。当前样例不宣称统计因果，需要结合指标、日志和拓扑证据。

## 验收与秋招表达

`tests/unit/test_change_intelligence.py` 和企业 Demo 覆盖查询、排序、依赖关联、理由字段与序列化。面试可说明：根因定位不只查日志，我把变更时间线作为独立证据源并输出可解释置信度。
