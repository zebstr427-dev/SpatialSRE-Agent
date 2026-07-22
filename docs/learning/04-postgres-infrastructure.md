# 第 4 课：建立 PostgreSQL Checkpoint 基础设施

对应提交：`0f8c657 feat: add PostgreSQL checkpoint infrastructure`

## 为什么使用独立 Compose

Milvus 与 Agent checkpoint 的升级、备份和故障域不同。`compose.postgres.yml` 单独管理 PostgreSQL，可以独立启动、停止和清理，也避免修改当前 Demo 的基础设施文件。

关键配置：

- PostgreSQL `18.4-alpine`。
- 只绑定 `127.0.0.1:5433`，不暴露到局域网。
- Docker named volume `oncall-postgres-data`。
- `pg_isready` 健康检查。
- `no-new-privileges` 安全选项。

Docker Hub 不可达时，默认镜像使用官方 Public ECR 镜像路径。

## 启动与验证

```powershell
docker compose -f compose.postgres.yml up -d
docker compose -f compose.postgres.yml ps
docker exec oncall-postgres pg_isready -U oncall_agent -d oncall_agent
```

预期容器状态为 `healthy`，`pg_isready` 输出 `accepting connections`。

验证版本和数据库：

```powershell
docker exec oncall-postgres psql -U oncall_agent -d oncall_agent -Atc "select version();"
```

Checkpoint saver 初始化后应出现：

- `checkpoint_migrations`
- `checkpoints`
- `checkpoint_blobs`
- `checkpoint_writes`

## 配置安全

`.env.example` 只能放本地开发占位配置。真实环境 DSN 写入被忽略的 `.env` 或 Secret Manager，不得进入 Git。

检查命令：

```powershell
git status --short --ignored
git ls-files | Select-String -Pattern "(^|/)\.env$|volumes|\.log$"
```

第二条命令预期没有输出。

## 常见错误

### 端口 5433 被占用

用 `Get-NetTCPConnection -LocalPort 5433` 找到占用进程，或在 `.env` 中改 `CHECKPOINT_POSTGRES_PORT`，同时更新测试 DSN。

### Docker Hub 超时

保留 `public.ecr.aws/docker/library/postgres:18.4-alpine`，或通过 `CHECKPOINT_POSTGRES_IMAGE` 指向可信镜像仓库。

## 面试问答

**问：为什么不用宿主机目录挂载？**

答：named volume 更少依赖 Windows/Linux 路径差异和文件权限，适合本地基础设施。生产环境则应使用托管数据库或明确的存储类和备份策略。

**问：健康检查和进程启动成功有什么区别？**

答：容器进程存在不代表数据库已经接受连接。`pg_isready` 检查的是服务可用阶段，依赖服务应等待健康状态。
