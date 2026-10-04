import os
import shutil

import pytest
from bedrock.artifacts import RunArtifactStore, RunReplayEngine
from bedrock.contracts import AgentState, Decision, DecisionType, ToolCall, ToolResult
from bedrock.events import Event, EventBus, EventLogger, EventType
from bedrock.memory.stores import InMemoryStore
from bedrock.memory import MemoryEntry, MemoryProvenance
from bedrock.policy import PolicyEngine, CapabilityManager


TEST_RUNS_DIR = "test_runs"


@pytest.fixture(autouse=True)
def cleanup_test_runs():
    yield
    if os.path.exists(TEST_RUNS_DIR):
        shutil.rmtree(TEST_RUNS_DIR)


def test_run_artifact_store_persists_run() -> None:
    store = RunArtifactStore(base_dir=TEST_RUNS_DIR)
    store.start_run("test-run-1", "session-1", "input data", {"role": "test"})
    store.record_event(Event(type=EventType.RUN_STARTED, data={"x": 1}))
    store.record_decision(
        Decision(type=DecisionType.TOOL, tool_call=ToolCall(tool="web.search", args={"q": "x"})),
        iteration=1,
    )
    store.record_tool_call(
        ToolCall(tool="web.search", args={"q": "x"}, call_id="call-1"),
        ToolResult(call_id="call-1", tool="web.search", success=True, output={"results": []}),
    )
    store.record_artifact("output.txt", "hello world")
    store.complete_run(success=True, final_output="done", iterations=1)

    run_dir = store.get_run_dir("test-run-1")
    assert run_dir is not None
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "artifacts" / "output.txt").exists()


def test_replay_engine_reconstructs_run() -> None:
    store = RunArtifactStore(base_dir=TEST_RUNS_DIR)
    store.start_run("replay-run", "session-2", "fix bug", {"role": "coder"})
    store.record_event(Event(type=EventType.TOOL_COMPLETED, data={"tool": "shell.execute"}))
    store.complete_run(success=False, final_output=None, iterations=3)

    engine = RunReplayEngine(artifact_store=store)
    result = engine.replay("replay-run")
    assert result["run_id"] == "replay-run"
    assert result["session_id"] == "session-2"
    assert result["success"] is False
    assert result["iterations"] == 3
    assert len(result["events"]) == 1
    assert result["events"][0]["type"] == "tool.completed"


@pytest.mark.asyncio
async def test_memory_store_write_read() -> None:
    store = InMemoryStore()
    entry = MemoryEntry(
        id="",
        content="test fact",
        memory_class="semantic",
        provenance=MemoryProvenance(source="test"),
    )
    memory_id = await store.write(entry)
    assert memory_id == entry.id
    loaded = await store.read(memory_id)
    assert loaded is not None
    assert loaded.content == "test fact"


@pytest.mark.asyncio
async def test_memory_store_search() -> None:
    store = InMemoryStore()
    entry = MemoryEntry(
        id="",
        content="python is great",
        memory_class="semantic",
        provenance=MemoryProvenance(source="test"),
        tags=["code"],
    )
    await store.write(entry)
    results = await store.search("python")
    assert len(results) == 1
    assert results[0].content == "python is great"


@pytest.mark.asyncio
async def test_policy_engine_default_allow() -> None:
    policy = PolicyEngine()
    assert await policy.check("web.search", {"query": "x"}, None) is True


@pytest.mark.asyncio
async def test_policy_engine_deny() -> None:
    from bedrock.policy import PermissionRule
    policy = PolicyEngine(rules=[PermissionRule(capability="web.search", allow=False)])
    assert await policy.check("web.search", {"query": "x"}, None) is False


def test_capability_manager() -> None:
    mgr = CapabilityManager(granted=["web.search"])
    assert mgr.has("web.search") is True
    assert mgr.has("shell.execute") is False
    mgr.grant("shell.execute")
    assert mgr.has("shell.execute") is True
    mgr.revoke("shell.execute")
    assert mgr.has("shell.execute") is False


def test_event_bus() -> None:
    bus = EventBus()
    logger = EventLogger()
    bus.subscribe(logger.handle)

    event_future = []

    def capture(event: Any) -> None:
        event_future.append(event)

    bus.subscribe(capture)
    import asyncio

    async def emit() -> None:
        await bus.emit(Event(type=EventType.RUN_STARTED, data={"x": 1}))

    asyncio.run(emit())
    assert len(event_future) == 1
    assert event_future[0].type == EventType.RUN_STARTED


def test_decision_types() -> None:
    decision = Decision(type=DecisionType.TOOL, tool_call=ToolCall(tool="web.search", args={"q": "x"}))
    assert decision.type == DecisionType.TOOL
    assert decision.tool_call.tool == "web.search"


@pytest.mark.asyncio
async def test_task_completion_evaluator_no_output() -> None:
    from bedrock.evaluators import TaskCompletionEvaluator
    evaluator = TaskCompletionEvaluator()
    state = AgentState(session_id="s")
    result = await evaluator.evaluate(state, None)
    assert result.passed is False
    assert result.score == 0.0


@pytest.mark.asyncio
async def test_task_completion_evaluator_with_output() -> None:
    from bedrock.evaluators import TaskCompletionEvaluator
    evaluator = TaskCompletionEvaluator()
    state = AgentState(session_id="s")
    result = await evaluator.evaluate(state, "fixed")
    assert result.passed is True
    assert result.score == 1.0


@pytest.mark.asyncio
async def test_unauthorized_action_evaluator_clean() -> None:
    from bedrock.evaluators import UnauthorizedActionEvaluator
    evaluator = UnauthorizedActionEvaluator()
    state = AgentState(session_id="s", history=[])
    result = await evaluator.evaluate(state, "done")
    assert result.passed is True
    assert result.score == 1.0


@pytest.mark.asyncio
async def test_regression_evaluator_detects_errors() -> None:
    from bedrock.evaluators import RegressionEvaluator
    evaluator = RegressionEvaluator()
    state = AgentState(session_id="s", history=[{"error": "something broke"}])
    result = await evaluator.evaluate(state, "output")
    assert result.passed is False
    assert result.score == 0.0