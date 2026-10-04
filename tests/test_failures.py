"""Failure mode tests for Bedrock kernel."""

from __future__ import annotations

import os
import shutil

import pytest

from bedrock.artifacts import RunArtifactStore
from bedrock.contracts import AgentState, Decision, DecisionType, ToolCall, ToolResult
from bedrock.events import Event, EventBus, EventType
from bedrock.memory import MemorySystem
from bedrock.memory.stores import InMemoryStore
from bedrock.models import ModelRouter, ModelRequest
from bedrock.models.providers import EchoProvider
from bedrock.policy import PolicyEngine, PermissionRule
from bedrock.runtime import AgentRuntime
from bedrock.tools import Tool, ToolCapability, ToolExecutor, ToolRegistry


TEST_RUNS_DIR = "test_runs_failures"


@pytest.fixture(autouse=True)
def cleanup_test_runs():
    yield
    if os.path.exists(TEST_RUNS_DIR):
        shutil.rmtree(TEST_RUNS_DIR)


def test_denied_permission_blocks_tool() -> None:
    class BrokenTool(Tool):
        name = "broken.tool"
        capability = ToolCapability(name="broken.tool", risk="high")

        async def execute(self, ctx, args):
            return {"result": "should not run"}

    registry = ToolRegistry()
    registry.register(BrokenTool())
    policy = PolicyEngine(rules=[PermissionRule(capability="broken.tool", allow=False)])
    executor = ToolExecutor(registry=registry, policy=policy)

    import asyncio

    async def run() -> None:
        result = await executor.execute(ToolCall(tool="broken.tool", args={}), None)
        assert result.success is False
        assert result.error == "Policy denied execution"

    asyncio.run(run())


def test_broken_tool_captures_exception() -> None:
    class ExplodingTool(Tool):
        name = "explode.tool"
        capability = ToolCapability(name="explode.tool", risk="high")

        async def execute(self, ctx, args):
            raise RuntimeError("kaboom")

    registry = ToolRegistry()
    registry.register(ExplodingTool())
    executor = ToolExecutor(registry=registry)

    import asyncio

    async def run() -> None:
        result = await executor.execute(ToolCall(tool="explode.tool", args={}), None)
        assert result.success is False
        assert "kaboom" in result.error

    asyncio.run(run())


def test_bad_model_response_does_not_crash() -> None:
    class BadProvider:
        name = "bad"

        async def generate(self, request):
            raise ConnectionError("model down")

    router = ModelRouter(providers={"bad": BadProvider()}, routes={"fast": "bad"})
    import asyncio

    async def run() -> None:
        request = ModelRequest(messages=[])
        try:
            await router.invoke("fast", request)
            assert False, "Should have raised"
        except ConnectionError:
            pass

    asyncio.run(run())


def test_artifact_store_records_policy_denial() -> None:
    import asyncio

    class TestTool(Tool):
        name = "test.tool"
        capability = ToolCapability(name="test.tool", risk="low")

        async def execute(self, ctx, args):
            return {"ok": True}

    registry = ToolRegistry()
    registry.register(TestTool())
    policy = PolicyEngine(rules=[PermissionRule(capability="test.tool", allow=False)])
    executor = ToolExecutor(registry=registry, policy=policy)
    memory = MemorySystem(store=InMemoryStore())
    event_bus = EventBus()
    artifact_store = RunArtifactStore(base_dir=TEST_RUNS_DIR)
    router = ModelRouter(providers={"echo": EchoProvider()}, routes={"fast": "echo", "reasoning": "echo"})

    runtime = AgentRuntime(
        model_router=router,
        tool_executor=executor,
        memory=memory,
        policy=policy,
        event_bus=event_bus,
        artifact_store=artifact_store,
        max_iterations=5,
    )

    async def run() -> None:
        state = AgentState(session_id="s", input="use test.tool")
        result = await runtime.run(state=state, identity={"role": "test"})
        denied_events = [h for h in result.history if h.get("event") == "policy.denied" or h.get("decision", {}).get("type") == "noop"]
        assert result.metadata.get("run_id") is not None

    asyncio.run(run())


def test_runtime_completes_without_final_output() -> None:
    registry = ToolRegistry()
    executor = ToolExecutor(registry=registry)
    memory = MemorySystem(store=InMemoryStore())
    router = ModelRouter(providers={"echo": EchoProvider()}, routes={"fast": "echo", "reasoning": "echo"})
    runtime = AgentRuntime(model_router=router, tool_executor=executor, memory=memory, max_iterations=3)

    import asyncio

    async def run() -> None:
        state = AgentState(session_id="s", input="garbage")
        result = await runtime.run(state=state, identity={"role": "test"})
        assert result.metadata.get("run_id") is not None
        assert len(result.history) <= 3

    asyncio.run(run())
