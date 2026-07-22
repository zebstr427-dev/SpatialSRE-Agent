# 第 7 课：证明重启恢复

对应提交：`28d7a05 test(postgres): prove durable graph recovery`

## “用了 PostgreSQL”不等于“证明可恢复”

真正的恢复测试必须跨越资源生命周期：

1. 第一组连接池和 graph 执行 `collect_evidence`。
2. graph 在该节点后中断，checkpoint 的 `next` 为 `finish_diagnosis`。
3. 关闭第一组连接池。
4. 创建第二组连接池和全新的 graph 实例。
5. 对同一 `thread_id` 使用 `ainvoke(None, config)` 继续。
6. 验证 evidence 未丢失，且 `collect_evidence` 总执行次数仍为 1。

如果第二次再次传入 initial state，就表示开始一次新输入，而不是从待执行节点恢复。恢复调用的关键是 `input=None` 与相同 `thread_id`。

## 确定性节点

集成测试不用真实 LLM 和 MCP，因为恢复测试关注的是 runtime 语义，不是模型质量。确定性节点具有三个优势：

- 输出固定，失败可复现。
- 计数器能精确证明节点是否重跑。
- 测试不消耗 token，不受网络和模型版本影响。

## 隔离测试

另一个测试在相同 `session_id` 下执行两个 incident，关闭连接池后用新 `AIOpsService` 读取。断言两个状态的 input、past_steps 和 incident ID 均独立。

测试生成 `integration-{uuid}` 作为 thread ID，并在 `finally` 中调用 `adelete_thread`，避免污染共享开发数据库。

## 执行命令

```powershell
docker compose -f compose.postgres.yml up -d
.\.venv\Scripts\pytest.exe -m postgres tests/integration/test_postgres_durable_runtime.py -q
```

预期结果：

```text
.. [100%]
2 passed
```

完整回归：

```powershell
.\.venv\Scripts\pytest.exe -q
```

预期为 `31 passed`。

## 常见错误

### 恢复时第一个节点再次执行

确认 thread ID 完全一致、第二次输入是 `None`，并检查第一次 checkpoint 的 `next`。若第一次已经到 END，就没有“继续”的节点。

### 测试偶尔读取到别的状态

不要复用固定 thread ID。每个测试使用 UUID，并在结束时按 thread 删除。

### PostgreSQL 测试卡住

检查容器健康和 DSN。测试默认连接 `127.0.0.1:5433`，也可通过 `TEST_CHECKPOINT_DATABASE_URL` 显式指定测试库。

## 面试问答

**问：checkpoint 能保证节点 exactly-once 吗？**

答：不能。checkpoint 能记录图进度，但进程可能在外部副作用完成后、checkpoint 写入前崩溃。工具调用仍需要幂等键、outbox/inbox、执行租约或人工审批。

**问：为什么关闭连接池后再恢复很重要？**

答：只在同一 graph 实例读取可能命中内存对象，无法证明持久化边界。重建 pool 和 graph 更接近进程重启，能够验证数据库中的 checkpoint 才是事实来源。

**问：下一阶段最合理的升级是什么？**

答：先加 Human-in-the-loop 和幂等执行协议，再扩展 AgentOps tracing/eval。多 Agent 应建立在可靠的单 Agent 状态、权限和恢复语义之上。
