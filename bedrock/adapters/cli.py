from __future__ import annotations

import asyncio
import sys
from typing import Optional

from bedrock.artifacts import RunArtifactStore
from bedrock.contracts import AgentState
from bedrock.runtime import AgentRuntime
from bedrock.memory import MemorySystem
from bedrock.memory.stores import InMemoryStore
from bedrock.models import ModelRouter
from bedrock.models.providers import EchoProvider
from bedrock.tools import ToolExecutor, ToolRegistry


async def run_cli(input_text: str, session_id: str = "default", artifact_store: Optional[RunArtifactStore] = None) -> AgentState:
    registry = ToolRegistry()
    executor = ToolExecutor(registry=registry)
    memory = MemorySystem(store=InMemoryStore())
    router = ModelRouter(providers={"echo": EchoProvider()}, routes={"fast": "echo", "reasoning": "echo"})
    runtime = AgentRuntime(
        model_router=router,
        tool_executor=executor,
        memory=memory,
        artifact_store=artifact_store,
    )

    state = AgentState(session_id=session_id, input=input_text)
    identity: dict = {}
    result = await runtime.run(state=state, identity=identity)
    return result


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: bedrock run <input>")
        sys.exit(1)
    input_text = " ".join(sys.argv[1:])
    artifact_store = RunArtifactStore(base_dir="runs")
    result = asyncio.run(run_cli(input_text, artifact_store=artifact_store))
    final = result.artifacts.get("final")
    if final:
        print(final.get("content", ""))
    else:
        print("No final output.")
