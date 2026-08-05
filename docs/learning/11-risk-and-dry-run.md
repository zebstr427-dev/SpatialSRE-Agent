# 第 11 课：风险等级与 Dry-run

## 实现位置与功能

- `app/agent/tool_risk.py`：定义 `READ_ONLY / WRITE / HIGH_RISK`，维护已知只读工具目录，未知工具默认高风险。
- `app/agent/tool_gateway.py`：注册时绑定风险元数据，执行前完成硬阻断和 dry-run 参数覆盖。
- `app/agent/aiops/executor.py`：所有 Agent 工具请求都显式使用 dry-run 模式。

## 核心行为

只读工具正常执行；写工具只有 `dry_run=True` 才能进入工具，而且 Gateway 会把注册的 dry-run 参数强制覆盖为 `True`，不信任 LLM 参数；高风险和未知工具在工具函数运行前返回 `tool_risk_blocked`。这是一条不可被 prompt 或策略配置绕过的安全底线。

## 验收与面试表达

单元测试证明只读放行、写操作模拟执行、高风险零调用和未知工具 fail closed。面试可以表述为：我把风险控制放在统一 Gateway 的执行边界，而不是靠提示词要求模型谨慎。
