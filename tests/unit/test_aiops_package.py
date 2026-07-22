import os
import subprocess
import sys


def test_state_module_import_does_not_require_external_credentials() -> None:
    environment = os.environ.copy()
    environment.pop("DASHSCOPE_API_KEY", None)

    result = subprocess.run(
        [sys.executable, "-c", "from app.agent.aiops.state import PlanExecuteState"],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode == 0, result.stderr
