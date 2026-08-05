# 第 13 课：Policy-as-Code

## 实现位置与功能

- `policies/tool-execution.json`：版本化策略，进入 Git 评审和变更追踪。
- `app/agent/policy.py`：Pydantic schema、UTF-8 JSON loader、条件匹配和决策模型。
- `app/agent/tool_gateway.py`：执行前求值 `allow / deny / require_approval`。
- `IncidentState.policy_decisions`：持久化策略版本、命中规则、理由、身份和风险。

## 决策语义

规则按声明顺序首个匹配生效，可按工具、角色、服务、风险和环境组合匹配；没有规则命中时执行默认拒绝。策略只能进一步收紧或要求审批，不能放行 Gateway 的高风险硬阻断和身份越界。

## 验收与面试表达

测试覆盖 schema 拒绝、文件加载、组合条件、首匹配、默认拒绝、Gateway 执行和 checkpoint 决策审计。面试可以表述为：权限变更由可评审策略文件驱动，并保留当次执行使用的策略版本，而不是散落在业务代码的 if 判断。
