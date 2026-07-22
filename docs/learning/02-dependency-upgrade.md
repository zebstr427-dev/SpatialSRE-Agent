# 第 2 课：受控升级 Agent 核心依赖

对应提交：`d179ba5 build: add PostgreSQL checkpoint dependencies`

## 最终版本边界

- `langgraph>=1.2.9,<2`
- `langgraph-checkpoint-postgres>=3.1.0,<4`
- `psycopg[binary]>=3.3.4,<4`
- checkpoint core 由 lockfile 解析为 `4.1.1`

版本范围写在 `pyproject.toml`，完整可复现依赖树写在 `uv.lock`。前者表达项目支持范围，后者表达本次构建的精确结果。

## 为什么不能只执行 pip install

Agent 框架更新快，`langgraph`、checkpoint 接口、LangChain Core 和序列化协议之间存在传递依赖。只在本机临时安装会导致：

- CI 和开发机解析出不同版本。
- 一次间接依赖升级改变运行语义。
- 无法回答“这个可运行版本到底用了什么”。

## 升级流程

```powershell
# 升级前
.\.venv\Scripts\pytest.exe -m "not postgres" -q

# 更新并锁定
uv lock --upgrade-package langgraph --upgrade-package langgraph-checkpoint-postgres
uv sync --extra dev

# 升级后跑同一测试集
.\.venv\Scripts\pytest.exe -m "not postgres" -q
```

核对安装版本：

```powershell
.\.venv\Scripts\python.exe -c "import importlib.metadata as m; print(m.version('langgraph')); print(m.version('langgraph-checkpoint-postgres')); print(m.version('psycopg'))"
```

预期输出包含 `1.2.9`、`3.1.0`、`3.3.4`。

## 常见错误

### Python 版本不满足

本项目约束是 Python `>=3.11,<3.14`。使用不匹配解释器时，应重建 `.venv`，不要修改 lockfile 去迁就错误环境。

### lockfile 出现大量无关更新

先确认是否使用了全量 `--upgrade`。生产升级应尽量指定 package，缩小兼容性回归范围。

## 面试问答

**问：直接依赖和传递依赖有什么区别？**

答：项目代码直接使用的是直接依赖；直接依赖内部要求的包是传递依赖。即使没有写进 `pyproject.toml`，传递依赖升级仍可能改变项目行为，所以需要 lockfile。

**问：为什么同时需要范围和 lockfile？**

答：范围用于声明兼容契约，lockfile 用于可复现部署。只有范围不够稳定，只有精确 pin 又无法表达可接受的升级边界。
