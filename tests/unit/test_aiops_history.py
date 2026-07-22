from app.agent.aiops.history import format_steps_for_prompt, format_steps_markdown
from app.agent.aiops.state import ExecutedStep


def _step(result: str = "cpu=95%") -> ExecutedStep:
    return {
        "step": "query metrics",
        "result": result,
        "status": "succeeded",
        "started_at": "2026-07-22T00:00:00+00:00",
        "finished_at": "2026-07-22T00:00:01+00:00",
    }


def test_format_steps_for_prompt_truncates_large_tool_results() -> None:
    text = format_steps_for_prompt([_step("x" * 305)], result_limit=300)

    assert text == f"步骤: query metrics\n结果: {'x' * 300}..."


def test_format_steps_markdown_preserves_full_result_and_status() -> None:
    text = format_steps_markdown([_step()])

    assert text == "### 步骤: query metrics\n**状态:** succeeded\n**结果:**\ncpu=95%"
