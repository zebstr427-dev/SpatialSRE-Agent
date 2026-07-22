# 第 0 课：可运行基线

记录时间：2026-07-22

## 当前运行状态

- FastAPI 监听 `http://127.0.0.1:9900`。
- `GET /health` 返回 HTTP 200。
- 服务名为 `SuperBizAgent`，版本为 `1.0.0`。
- Milvus 状态为 `connected`。
- AIOps 当前使用 LangGraph `MemorySaver`，进程退出后状态会丢失。

## 基线检查命令

```powershell
Invoke-RestMethod http://127.0.0.1:9900/health | ConvertTo-Json -Depth 6
git status --short --ignored
```

## 安全边界

以下内容不得进入 Git：

- `.env` 与本地 MCP 配置
- `logs/` 与 `*.log`
- `.venv/`
- `volumes/` 中的 Milvus、MinIO、etcd 数据
- `uploads/`

这次提交用于建立可回退的源码快照。后续每个课程模块都在独立提交中完成。
