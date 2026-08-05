"""LangChain tools backed by the Change Intelligence repository."""

import json
from collections.abc import Sequence

from langchain_core.tools import BaseTool, StructuredTool

from app.change_intelligence import ChangeRepository, default_change_repository


def create_change_tools(repository: ChangeRepository) -> tuple[BaseTool, ...]:
    def build(name: str, change_types: set[str]) -> BaseTool:
        async def query(service: str, start: str, end: str) -> str:
            records = repository.query(
                service=service,
                start=start,
                end=end,
                change_types=change_types,
            )
            return json.dumps(
                [item.to_record() for item in records],
                ensure_ascii=False,
            )

        return StructuredTool.from_function(
            coroutine=query,
            name=name,
            description=f"Query {name.replace('_', ' ')} in a time window",
        )

    definitions: Sequence[tuple[str, set[str]]] = (
        ("query_recent_deployments", {"deployment", "image"}),
        ("query_config_changes", {"config"}),
        ("query_git_commits", {"git"}),
        ("query_k8s_rollout_history", {"k8s_rollout"}),
    )
    return tuple(build(name, types) for name, types in definitions)


DEFAULT_CHANGE_TOOLS = create_change_tools(default_change_repository())
