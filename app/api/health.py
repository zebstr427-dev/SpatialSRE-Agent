"""健康检查接口"""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import config
from app.core.milvus_client import milvus_manager

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):

    """健康检查接口
    检查服务状态和数据库连接状态

    Returns:
        JSONResponse: 健康检查结果
    """
    # 检查服务基本状态
    health_data: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
        "service": config.app_name,
        "version": config.app_version,
        "status": "healthy"
    }

    # 检查 Milvus 连接状态
    try:
        milvus_healthy = milvus_manager.health_check()
        milvus_status: str = "connected" if milvus_healthy else "disconnected"
        milvus_message: str = "Milvus 连接正常" if milvus_healthy else "Milvus 连接异常"
        health_data["milvus"] = {
            "status": milvus_status,
            "message": milvus_message
        }
    except Exception as e:
        logger.warning(f"Milvus 健康检查失败: {e}")
        health_data["milvus"] = {
            "status": "error",
            "message": f"Milvus 检查失败: {str(e)}"
        }

    checkpoint_runtime = getattr(request.app.state, "checkpoint_runtime", None)
    try:
        checkpoint_healthy = (
            checkpoint_runtime is not None
            and await checkpoint_runtime.health_check()
        )
        health_data["checkpoint_store"] = {
            "status": "connected" if checkpoint_healthy else "disconnected",
            "message": (
                "PostgreSQL checkpoint store 连接正常"
                if checkpoint_healthy
                else "PostgreSQL checkpoint store 连接异常"
            ),
        }
    except Exception as e:
        logger.warning(f"Checkpoint store 健康检查失败: {e}")
        health_data["checkpoint_store"] = {
            "status": "error",
            "message": f"Checkpoint store 检查失败: {str(e)}",
        }

    # 判断整体健康状态
    overall_status = "healthy"
    status_code = 200

    # 任一持久化依赖不可用时，服务不可用
    if any(
        health_data[dependency]["status"] != "connected"
        for dependency in ("milvus", "checkpoint_store")
    ):
        overall_status = "unhealthy"
        status_code = 503
        health_data["error"] = "持久化依赖不可用"

    health_data["status"] = overall_status

    return JSONResponse(
        status_code=status_code,
        content={
            "code": status_code,
            "message": "服务运行正常" if overall_status == "healthy" else "服务不可用",
            "data": health_data
        }
    )
