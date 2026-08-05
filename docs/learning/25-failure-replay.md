# 第 25 课：Failure Replay 基础

## 项目位置与功能

- `incident_cases/cpu_high_usage/`：告警、指标、日志、变更和 gold expectation 分文件保存。
- `app/replay/models.py`：case、工具调用、观察结果的不可变数据契约。
- `app/replay/core.py`：fixture loader、隔离工具箱和模拟器。

Replay 将一次故障演示变成可重复实验。工具只能访问 case 明确提供的固定响应，调用未声明工具立即失败；观察结果中的工具序列必须与 simulator 实际记录一致，防止测试伪造执行轨迹。

## 设计亮点与边界

隔离性是第一目标：回放不得访问真实生产系统，也不依赖当前 Prometheus/MCP 状态。当前只有 CPU case，框架已支持按目录扩展；更多 case 应覆盖失败、审批拒绝和证据不足，而不是只堆成功样例。

## 验收与秋招表达

`tests/unit/test_failure_replay.py` 验证 fixture 加载、固定工具响应、调用顺序和越界保护。面试可将它类比为 Agent 的“故障录制回放测试台”。
