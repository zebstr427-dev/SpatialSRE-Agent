# 第 26 课：Replay 指标与报告

## 项目位置与功能

`app/replay/metrics.py` 计算 root-cause hit、工具准确率/F1、证据覆盖、幻觉引用、延迟和成本，并输出稳定 JSON 报告。指标把“最终答案对不对”和“过程是否按正确工具、证据完成”分开。

## 关键设计

工具序列采用多重集合语义，重复调用不会被集合去重掩盖；证据覆盖只认可 gold evidence ID；报告引用未出现在 observation evidence 中即标记 hallucination。延迟和 token cost 原样保存，便于版本回归。

## 边界与验收

字符串 root-cause hit 是确定性基线，不解决语义等价表达；生产可增加 judge，但应保留当前无模型指标作为稳定门禁。`tests/unit/test_failure_replay.py` 覆盖正确根因、工具 F1、证据覆盖、伪造引用和 JSON 报告写入。

面试可表述为：我不仅评最终文本，还评工具轨迹、证据完整性、安全性和运行成本。
