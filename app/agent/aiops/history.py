"""Pure formatting helpers for structured AIOps execution history."""

from app.agent.aiops.state import ExecutedStep


def format_steps_for_prompt(steps: list[ExecutedStep], *, result_limit: int = 300) -> str:
    """Format bounded step results for a replanning prompt."""

    formatted: list[str] = []
    for step in steps:
        result = step["result"]
        if len(result) > result_limit:
            result = f"{result[:result_limit]}..."
        formatted.append(f"步骤: {step['step']}\n结果: {result}")
    return "\n".join(formatted)


def format_steps_markdown(steps: list[ExecutedStep]) -> str:
    """Format complete step results for the final diagnosis prompt."""

    return "\n\n".join(
        (
            f"### 步骤: {step['step']}\n"
            f"**状态:** {step['status']}\n"
            f"**结果:**\n{step['result']}"
        )
        for step in steps
    )
