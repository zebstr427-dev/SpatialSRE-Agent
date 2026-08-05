# 第 16 课：Runbook-as-Code 基础

## 项目位置与功能

- `app/runbooks.py`：Pydantic schema、YAML loader、版本校验、注册表和告警匹配。
- `runbooks/*.yaml`：CPU、内存、不可用、慢响应、磁盘五类核心故障流程。

这一层把散落在文档和工程师经验里的排障步骤变成可版本化的数据契约。每个 Runbook 明确触发条件、工具步骤、停止条件、审批动作和预期证据，加载时拒绝重复 ID、非法版本和未知字段。

## 设计亮点与边界

Runbook 是受控执行路径，不是另一段 prompt。Git diff 可以审查运维流程变化，测试可以验证步骤顺序，运行时只持久化 JSON-safe 记录。当前使用本地 YAML registry；生产扩展可增加签名、发布审批和集中分发，但不能绕过 schema 校验。

## 验收与秋招表达

`tests/unit/test_runbooks.py` 覆盖五个文件加载、schema 失败、重复注册和确定性匹配。面试可表述为：我用 Runbook-as-Code 将隐性运维经验转成可 review、可审计、可评测的执行资产。
