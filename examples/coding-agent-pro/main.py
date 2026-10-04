"""Coding Agent Pro — reference application built on Bedrock kernel.

Proves that a real application can be built, debugged, evaluated, replayed,
and extended without changing anything inside bedrock/kernel/.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bedrock.artifacts import RunArtifactStore, RunReplayEngine
from bedrock.contracts import AgentState
from bedrock.context import ContextCompiler, ContextBudget
from bedrock.events import EventBus, EventLogger
from bedrock.memory import MemorySystem
from bedrock.memory.stores import InMemoryStore
from bedrock.models import ModelRouter
from bedrock.models.providers import EchoProvider
from bedrock.policy import CapabilityManager, PolicyEngine
from bedrock.runtime import AgentRuntime
from bedrock.tools import ToolExecutor, ToolRegistry
from bedrock.workflows import WorkflowDefinition, WorkflowExecutor

CODING_PACK_PATH = Path(__file__).parent.parent.parent / "packs" / "coding" / "__init__.py"
FS_PACK_PATH = Path(__file__).parent.parent.parent / "packs" / "filesystem" / "__init__.py"


def _import_pack(path: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("pack", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PACK


async def run_coding_agent(repo_path: str, task: str) -> None:
    registry = ToolRegistry()

    coding_pack = _import_pack(CODING_PACK_PATH)
    fs_pack = _import_pack(FS_PACK_PATH)
    for tool in coding_pack["tools"]:
        registry.register(tool)
    for tool in fs_pack["tools"]:
        registry.register(tool)

    capabilities = CapabilityManager(granted=[t.name for t in registry.all().values()])
    policy = PolicyEngine()
    executor = ToolExecutor(registry=registry, policy=policy)
    memory = MemorySystem(store=InMemoryStore())
    budget = ContextBudget(max_tokens=16000)
    compiler = ContextCompiler(budget=budget)
    event_bus = EventBus()
    artifact_store = RunArtifactStore(base_dir="runs")

    router = ModelRouter(
        providers={"echo": EchoProvider()},
        routes={"fast": "echo", "reasoning": "echo"},
    )

    runtime = type("CodingRuntime", (), {})()
    # Use AgentRuntime directly via composition — no kernel modification needed
    from bedrock.runtime import AgentRuntime
    agent = AgentRuntime(
        model_router=router,
        tool_executor=executor,
        memory=memory,
        context_compiler=compiler,
        policy=policy,
        event_bus=event_bus,
        artifact_store=artifact_store,
        max_iterations=20,
    )

    state = AgentState(
        session_id="coding-session",
        input=f"Task: {task}\nRepository: {repo_path}",
    )
    identity = {
        "role": "repository-engineer",
        "objective": "diagnose and fix code issues with evidence-first rigor",
        "style": "minimal-diff, test-validated",
        "constraints": {
            "speculate": False,
            "citations_required": True,
            "require_tests": True,
            "max_diff_size": 500,
        },
    }

    result = await agent.run(state=state, identity=identity)
    final = result.artifacts.get("final")
    run_id = result.metadata.get("run_id", "unknown")
    print(f"Run ID: {run_id}")
    if final:
        print(f"Result: {final.get('content', '')}")
    else:
        print("No final output produced.")


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python main.py <repo_path> <task>")
        print("Example: python main.py . 'Fix the failing tests'")
        sys.exit(1)
    repo_path = sys.argv[1]
    task = " ".join(sys.argv[2:])
    asyncio.run(run_coding_agent(repo_path=repo_path, task=task))


if __name__ == "__main__":
    main()
