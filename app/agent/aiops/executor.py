"""
Executor 节点：执行单个步骤
基于 LangGraph 官方教程实现
"""

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_qwq import ChatQwen
from loguru import logger

from app.agent.identity import AgentIdentity
from app.agent.approval import create_approval_request
from app.agent.evidence import create_tool_evidence
from app.agent.tool_gateway import ToolExecutionResult, create_tool_gateway
from app.config import config
from app.change_intelligence import ChangeRecord

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
    identity = AgentIdentity.from_record(state["identity"])
    started_at = utc_now_iso()
    tool_call_audits: list[ToolCallAuditRecord] = []
    policy_decisions: list[dict[str, object]] = []
    evidence_records: list[dict[str, object]] = []
    change_records: list[dict[str, object]] = []
    pending_tool_calls = list(state.get("pending_tool_calls", []))
    runbook_steps = list(state.get("runbook_steps", []))
    remaining_runbook_steps = runbook_steps[1:] if runbook_steps else []
    approval_decision = state.get("approval_decision")
    logger.info(f"当前任务: {task}")

    if pending_tool_calls and approval_decision is not None:
        if not bool(approval_decision.get("approved")):
            decided_by = str(approval_decision.get("decided_by", "unknown"))
            reason = approval_decision.get("reason") or "no reason provided"
            return {
                "plan": plan[1:],
                "past_steps": [
                    create_executed_step(
                        task,
                        f"Tool approval rejected by {decided_by}: {reason}",
                        status="failed",
                        started_at=started_at,
                    )
                ],
                "pending_tool_calls": [],
                "runbook_steps": remaining_runbook_steps,
                "approval_decision": None,
                "tool_calls": [],
                "policy_decisions": [],
                "updated_at": utc_now_iso(),
            }

    def record_tool_call(result: ToolExecutionResult) -> None:
        if result.policy_decision is not None:
            policy_decisions.append(dict(result.policy_decision))
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
                identity_id=result.identity_id,
                risk_level=result.risk_level.value,
                dry_run=result.dry_run,
            )
        )

    try:
        gateway = await create_tool_gateway(audit_hook=record_tool_call)
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
                content=(
                    "你负责执行一个诊断步骤。只能使用已注册工具，"
                    "必须基于真实工具结果，不得编造数据。"
                )
            ),
            HumanMessage(content=f"请执行以下任务: {task}"),
        ]

        if pending_tool_calls:
            llm_response = AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": str(item["tool_call_id"]),
                        "name": str(item["tool_name"]),
                        "args": dict(item.get("arguments", {})),
                    }
                    for item in pending_tool_calls
                ],
            )
        elif runbook_steps:
            runbook_step = runbook_steps[0]
            runbook_arguments = dict(runbook_step.get("arguments", {}))
            alert = state.get("alert", {})
            service = alert.get("service")
            if isinstance(service, str) and "service" not in runbook_arguments:
                runbook_arguments["service"] = service
            llm_response = AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": (
                            f"runbook-{state['incident_id']}-"
                            f"{runbook_step['id']}"
                        ),
                        "name": str(runbook_step["tool"]),
                        "args": runbook_arguments,
                    }
                ],
            )
        else:
            llm_response = await llm_with_tools.ainvoke(messages)
        logger.info(f"LLM 响应类型: {type(llm_response)}")

        if hasattr(llm_response, "tool_calls") and llm_response.tool_calls:
            messages.append(llm_response)
            tool_results: list[ToolExecutionResult] = []
            approved = bool(
                approval_decision and approval_decision.get("approved")
            )
            for tool_call in llm_response.tool_calls:
                tool_results.append(
                    await gateway.invoke(
                        tool_call_id=str(tool_call["id"]),
                        tool_name=str(tool_call["name"]),
                        arguments=dict(tool_call.get("args", {})),
                        dry_run=True,
                        identity=identity,
                        approval_granted=approved,
                    )
                )

            approval_results = [
                item
                for item in tool_results
                if item.error_code == "tool_approval_required"
            ]
            if approval_results:
                requests = list(state.get("approval_requests", []))
                pending_records: list[dict[str, object]] = []
                for item in approval_results:
                    decision = item.policy_decision or {}
                    request = create_approval_request(
                        incident_id=state["incident_id"],
                        identity_id=identity.identity_id,
                        tool_call_id=item.tool_call_id,
                        tool_name=item.tool_name,
                        arguments=item.arguments,
                        risk_level=item.risk_level,
                        policy_decision_id=str(decision.get("decision_id", "")),
                    )
                    requests.append(request.to_record())
                    pending_records.append(
                        {
                            "tool_call_id": item.tool_call_id,
                            "tool_name": item.tool_name,
                            "arguments": dict(item.arguments),
                        }
                    )
                return {
                    "pending_tool_calls": pending_records,
                    "approval_requests": requests,
                    "tool_calls": tool_call_audits,
                    "policy_decisions": policy_decisions,
                    "evidence": evidence_records,
                    "updated_at": utc_now_iso(),
                }

            for item in tool_results:
                if item.status != "succeeded":
                    continue
                decision = item.policy_decision or {}
                evidence_records.append(
                    create_tool_evidence(
                        tool_call_id=item.tool_call_id,
                        tool_name=item.tool_name,
                        arguments=item.arguments,
                        output=item.output,
                        identity_id=item.identity_id,
                        risk_level=item.risk_level.value,
                        dry_run=item.dry_run,
                        started_at=item.started_at,
                        finished_at=item.finished_at,
                        policy_decision_id=(
                            str(decision["decision_id"])
                            if decision.get("decision_id")
                            else None
                        ),
                    )
                )
                if item.tool_name.startswith(
                    (
                        "query_recent_deployments",
                        "query_config_changes",
                        "query_git_commits",
                        "query_k8s_rollout_history",
                    )
                ):
                    parsed = json.loads(item.output)
                    change_records.extend(
                        ChangeRecord.model_validate(record).to_record()
                        for record in parsed
                    )

            failed_results = [
                item for item in tool_results if item.status == "failed"
            ]
            if failed_results:
                failure_summary = "; ".join(
                    f"{item.tool_name} [{item.error_code}]: "
                    f"{item.error_message or item.output}"
                    for item in failed_results
                )
                raise RuntimeError(f"Tool execution failed: {failure_summary}")

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
            result = getattr(final_response, "content", str(final_response))
        else:
            result = getattr(llm_response, "content", str(llm_response))

        result = str(result)
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
            "pending_tool_calls": [],
            "runbook_steps": remaining_runbook_steps,
            "approval_decision": None,
            "tool_calls": tool_call_audits,
            "policy_decisions": policy_decisions,
            "evidence": evidence_records,
            "change_records": change_records,
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
            "pending_tool_calls": [],
            "runbook_steps": remaining_runbook_steps,
            "approval_decision": None,
            "tool_calls": tool_call_audits,
            "policy_decisions": policy_decisions,
            "evidence": evidence_records,
            "change_records": change_records,
            "updated_at": utc_now_iso(),
        }
