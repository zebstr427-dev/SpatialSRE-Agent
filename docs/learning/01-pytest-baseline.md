# 第 1 课：建立 pytest 测试基线

对应提交：`df3591f test: establish agent runtime baseline`

## 为什么先写 characterization tests

旧系统没有测试时，直接重构会遇到一个问题：失败究竟来自新设计，还是旧行为被意外改变？Characterization test 不判断旧设计是否优雅，它先把当前可观察行为固定下来，作为升级前后的共同标尺。

本课建立两层测试：

- `tests/unit`：不连接 LLM、MCP、Milvus、PostgreSQL。
- `tests/integration`：通过 marker 显式声明外部依赖。

`tests/conftest.py` 还会在 Windows 上设置 Selector event loop，为 Psycopg 异步连接兼容性做准备。

## 关键配置

`pyproject.toml` 中的重要配置：

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
  "postgres: integration tests that require the local PostgreSQL checkpoint store",
]
```

严格 marker 可以防止把 `@pytest.mark.postgres` 拼错后悄悄当成普通测试运行。

## 执行命令

```powershell
uv sync --extra dev
.\.venv\Scripts\pytest.exe -m "not postgres" -q
```

预期结果是全部通过，并生成终端覆盖率摘要与 `htmlcov/`。`htmlcov/` 必须被 Git 忽略。

## 常见错误

### `uv` 不是可识别命令

当前 PowerShell 没有继承安装目录。可以重新加入 PATH，或直接使用已经创建好的 `.venv\Scripts\pytest.exe`。

### 导入模块时要求 API Key

说明模块导入阶段创建了 LLM、MCP 客户端或业务单例。正确做法是延迟导入，并通过构造函数注入测试替身。

## 面试问答

**问：单元测试为什么不能连接 PostgreSQL？**

答：单元测试要快速、确定并能并行运行。数据库协议、网络和容器生命周期属于集成边界，应该由 marker 隔离的集成测试覆盖。

**问：测试覆盖率越高越好吗？**

答：覆盖率只能说明代码被执行过，不能证明断言有效。Agent 项目更应该覆盖状态转换、工具调用边界、恢复语义和错误路径。
