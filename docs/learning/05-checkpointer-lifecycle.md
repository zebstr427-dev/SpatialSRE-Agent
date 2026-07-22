# 第 5 课：实现生产型 Checkpointer 生命周期

对应提交：`8cce7bb feat: manage durable runtime lifecycle`

## 资源所有权

连接池是进程级资源，应该由 FastAPI lifespan 创建和关闭：

```text
startup
  -> open AsyncConnectionPool
  -> create AsyncPostgresSaver
  -> setup checkpoint schema
  -> create AIOpsService(checkpointer)
request handling
shutdown
  -> close pool
```

模块导入阶段创建全局 `AIOpsService` 会导致测试导入即连接外部系统、热重载创建多份资源，也无法明确关闭连接池。现在 API 通过 `request.app.state.aiops_service` 获取 lifespan 所有的实例。

## 连接参数为什么重要

```python
kwargs={
    "autocommit": True,
    "prepare_threshold": 0,
    "row_factory": dict_row,
}
```

- `autocommit=True`：checkpoint setup 和写入不被遗留事务阻塞。
- `prepare_threshold=0`：避免连接池与 prepared statement 状态造成兼容问题。
- `dict_row`：checkpoint saver 按列名读取结果。

池设置 `min_size`、`max_size`、`timeout`，防止无限创建连接或永久等待。

## 反序列化安全

```python
JsonPlusSerializer(
    pickle_fallback=False,
    allowed_msgpack_modules=None,
)
```

checkpoint 数据可能被篡改。关闭 pickle fallback 并禁止重建任意模块对象，可把不可信对象恢复成基础字典，避免反序列化触发任意代码执行。

## Windows 事件循环

Psycopg 异步连接不支持 Windows 默认 Proactor event loop。`app/run.py` 和测试配置会在创建事件循环前设置 `WindowsSelectorEventLoopPolicy`。

正确启动：

```powershell
.\.venv\Scripts\python.exe -m app.run
```

## 验证命令

```powershell
.\.venv\Scripts\pytest.exe tests/unit/test_checkpoint_runtime.py -q
```

## 常见错误

### `Psycopg cannot use the ProactorEventLoop`

说明 uvicorn 在设置 Selector policy 之前已经创建事件循环。使用 `python -m app.run`，不要绕过项目入口直接调用异步代码。

### 服务关闭后 Python 不退出

通常是连接池或客户端没有放进 lifespan/finally。检查 `pool.closed`，并确保所有资源由创建它的层负责关闭。

## 面试问答

**问：依赖注入在这里解决了什么？**

答：它分离业务图和持久化实现。生产注入 PostgreSQL saver，单元测试注入 InMemorySaver，节点也可以注入确定性函数，从而不依赖真实 LLM。

**问：为什么数据库不可用时不回退 MemorySaver？**

答：静默降级会制造“请求成功但重启后数据丢失”的假象。durability 是接口契约，无法满足时应启动失败并由编排平台告警。
