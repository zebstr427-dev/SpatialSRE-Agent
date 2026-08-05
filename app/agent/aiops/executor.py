"""
Executor 节点：执行单个步骤
基于 LangGraph 官方教程实现
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_qwq import ChatQwen
from loguru import logger

from app.agent.tool_gateway import ToolExecutionResult, create_tool_gateway
from app.config import config

from .state import (
    IncidentState,
    ToolCallAuditRecord,
    create_executed_step,
    create_tool_call_audit_record,
    utc_now_iso,
)


async def executor(state: IncidentState) -> dict[str, Any]:
    """Execute the next planned step through the Tool Gateway."""
    logger.info("=== Executor：执行步骤 ===")

    plan = state.get("plan", [])
    if not plan:
        logger.info("计划为空，跳过执行")
        return {}

    task = plan[0]
    started_at = utc_now_iso()
    tool_call_audits: list[ToolCallAuditRecord] = []
    logger.info(f"当前任务: {task}")

    def record_tool_call(result: ToolExecutionResult) -> None:
        tool_call_audits.append(
            create_tool_call_audit_record(
                tool_call_id=result.tool_call_id,
                tool_name=result.tool_name,
                step=task,
                arguments=dict(result.arguments),
                result=result.output,
                status=result.status,
                started_at=result.started_at,
                finished_at=result.finished_at,
            )
        )

    try:
        gateway = await create_tool_gateway(
            audit_hook=record_tool_call
        )
        all_tools = gateway.list_tools()
        logger.info(f"Gateway 可用工具数量: {len(all_tools)}")

        llm = ChatQwen(
            model=config.rag_model,
            api_key=config.dashscope_api_key,
            temperature=0,
        )
        llm_with_tools = llm.bind_tools(all_tools)

        messages = [
            SystemMessage(
                content="""你是一个能力强大的助手，负责执行具体的任务步骤。

你可以使用各种工具来完成任务。对于每个步骤：
1. 理解步骤的目标
2. 选择合适的工具，如果已经指定了工具，则使用指定的工具
3. 调用工具获取信息
4. 返回执行结果

注意：
- 如果工具调用失败，请说明失败原因
- 不要编造数据，只返回实际获取的信息
- 执行结果要清晰、准确
- 专注于当前步骤，不要考虑其他任务"""
            ),
            HumanMessage(content=f"请执行以下任务: {task}"),
        ]

        llm_response = await llm_with_tools.ainvoke(messages)
        logger.info(f"LLM 响应类型: {type(llm_response)}")

        if hasattr(llm_response, "tool_calls") and llm_response.tool_calls:
            logger.info(
                f"检测到 {len(llm_response.tool_calls)} 个工具调用"
            )
            messages.append(llm_response)
            tool_results: list[ToolExecutionResult] = []

            for tool_call in llm_response.tool_calls:
                tool_results.append(
                    await gateway.invoke(
                        tool_call_id=str(tool_call["id"]),
                        tool_name=str(tool_call["name"]),
                        arguments=dict(tool_call.get("args", {})),
                        dry_run=True,
                    )
                )

            failed_results = [
                result
                for result in tool_results
                if result.status == "failed"
            ]
            if failed_results:
                failure_summary = "; ".join(
                    (
                        f"{item.tool_name} [{item.error_code}]: "
                        f"{item.error_message or item.output}"
                    )
                    for item in failed_results
                )
                raise RuntimeError(
                    f"Tool execution failed: {failure_summary}"
                )

            messages.extend(
                ToolMessage(
                    content=item.output,
                    tool_call_id=item.tool_call_id,
                    name=item.tool_name,
                    status="success",
                )
                for item in tool_results
            )
            final_response = await llm_with_tools.ainvoke(messages)
            result = (
                final_response.content
                if hasattr(final_response, "content")
                else str(final_response)
            )
        else:
            logger.info("LLM 未调用工具，直接返回结果")
            result = (
                llm_response.content
                if hasattr(llm_response, "content")
                else str(llm_response)
            )

        result = str(result)
        logger.info(f"步骤执行完成，结果长度: {len(result)}")

        return {
            "plan": plan[1:],
            "past_steps": [
                create_executed_step(
                    task,
                    result,
                    status="succeeded",
                    started_at=started_at,
                )
            ],
            "tool_calls": tool_call_audits,
            "updated_at": utc_now_iso(),
        }

    except Exception as exc:
        logger.error(f"执行步骤失败: {exc}", exc_info=True)
        return {
            "plan": plan[1:],
            "past_steps": [
                create_executed_step(
                    task,
                    f"执行失败: {exc}",
                    status="failed",
                    started_at=started_at,
                )
            ],
            "tool_calls": tool_call_audits,
            "updated_at": utc_now_iso(),
        }
