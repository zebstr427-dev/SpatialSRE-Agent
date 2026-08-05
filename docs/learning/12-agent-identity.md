# 第 12 课：Agent Identity

## 实现位置与功能

- `app/agent/identity.py`：不可变身份模型，包含身份 ID、角色、工具范围、服务范围和风险上限。
- `app/models/aiops.py`、`app/api/aiops.py`：接收身份并传给服务。
- `app/services/aiops_service.py`、`app/agent/aiops/state.py`：将身份保存为 checkpoint-safe 原始值。
- `app/agent/tool_gateway.py`：按工具范围、服务范围、风险上限依次执行强制门禁。

## 设计亮点

身份不是展示字段，而是每次工具调用的 mandatory guardrail。范围支持 glob 模式，但 checkpoint 只保存 JSON 值；工具审计同时记录 `identity_id / risk_level / dry_run`，因此跨 PostgreSQL 恢复后仍可追责。

## 验收与面试表达

测试覆盖身份序列化、范围匹配、风险上限、API 到状态传播及 Gateway 拒绝。面试可以表述为：我为 Agent 建立了类似服务账号的执行身份，使权限跟随每个 incident 和工具调用传播。
