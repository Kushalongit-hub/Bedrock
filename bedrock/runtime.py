from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from bedrock.artifacts import RunArtifactStore
from bedrock.contracts import AgentState, Decision, DecisionType, FinalOutput, ToolCall, ToolResult
from bedrock.context import ContextCompiler
from bedrock.events import Event, EventBus, EventType
from bedrock.memory import MemorySystem
from bedrock.models import ModelRequest, ModelRouter
from bedrock.policy import PolicyEngine
from bedrock.tools import ToolExecutor


class AgentRuntime:
    """Core agent runtime that drives the perception-decision-action loop."""

    def __init__(
        self,
        model_router: ModelRouter,
        tool_executor: ToolExecutor,
        memory: MemorySystem,
        context_compiler: Optional[ContextCompiler] = None,
        policy: Optional[PolicyEngine] = None,
        event_bus: Optional[EventBus] = None,
        artifact_store: Optional[RunArtifactStore] = None,
        max_iterations: int = 20,
    ) -> None:
        self.model_router = model_router
        self.tool_executor = tool_executor
        self.memory = memory
        self.context_compiler = context_compiler or ContextCompiler()
        self.policy = policy or PolicyEngine()
        self.event_bus = event_bus or EventBus()
        self.artifact_store = artifact_store
        self.max_iterations = max_iterations

        if artifact_store is not None:
            self.event_bus.subscribe(artifact_store.record_event)

    async def run(
        self,
        state: AgentState,
        identity: Dict[str, Any],
        expected: Optional[Any] = None,
    ) -> AgentState:
        run_id = str(uuid.uuid4())[:8]
        await self.event_bus.emit(
            Event(type=EventType.RUN_STARTED, run_id=run_id, data={"session_id": state.session_id})
        )

        if self.artifact_store:
            self.artifact_store.start_run(run_id, state.session_id, state.input, identity)

        state.metadata["run_id"] = run_id

        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            context = await self.context_compiler.compile(
                identity=identity,
                state=state,
                memories=await self.memory.recall(state.input or ""),
            )

            decision = await self._decide(context, identity)
            state.history.append({
                "iteration": iteration,
                "decision": decision.model_dump(mode="json"),
            })

            if self.artifact_store:
                self.artifact_store.record_decision(decision, iteration)

            if decision.type == DecisionType.FINAL:
                state.artifacts["final"] = decision.final_output.model_dump() if decision.final_output else None
                await self.event_bus.emit(
                    Event(type=EventType.AGENT_COMPLETED, run_id=run_id, data={"output": state.artifacts["final"]})
                )
                break

            if decision.type == DecisionType.TOOL and decision.tool_call:
                await self.event_bus.emit(
                    Event(
                        type=EventType.TOOL_REQUESTED,
                        run_id=run_id,
                        data={"tool": decision.tool_call.tool, "args": decision.tool_call.args},
                    )
                )

                allowed = await self.policy.check(decision.tool_call.tool, decision.tool_call.args, state)
                if not allowed:
                    await self.event_bus.emit(
                        Event(type=EventType.POLICY_DENIED, run_id=run_id, data={"tool": decision.tool_call.tool})
                    )
                    continue

                await self.event_bus.emit(
                    Event(type=EventType.TOOL_AUTHORIZED, run_id=run_id, data={"tool": decision.tool_call.tool})
                )
                await self.event_bus.emit(
                    Event(type=EventType.TOOL_STARTED, run_id=run_id, data={"tool": decision.tool_call.tool})
                )

                result = await self.tool_executor.execute(decision.tool_call, state)

                await self.event_bus.emit(
                    Event(
                        type=EventType.TOOL_COMPLETED if result.success else EventType.TOOL_FAILED,
                        run_id=run_id,
                        data={"tool": result.tool, "success": result.success, "error": result.error},
                    )
                )

                state.history.append({
                    "tool": result.model_dump(mode="json"),
                })
                if result.success and result.output is not None:
                    state.artifacts[f"tool_{decision.tool_call.tool}"] = result.output

                if self.artifact_store:
                    self.artifact_store.record_tool_call(decision.tool_call, result)

            if decision.type == DecisionType.NOOP:
                continue

        final_output = state.artifacts.get("final")
        success = final_output is not None
        await self.event_bus.emit(
            Event(type=EventType.RUN_COMPLETED, run_id=run_id, data={"iterations": iteration})
        )

        if self.artifact_store:
            self.artifact_store.complete_run(success=success, final_output=final_output, iterations=iteration)

        return state

    async def _decide(self, context: Any, identity: Dict[str, Any]) -> Decision:
        """Delegate to model router for a decision."""
        from bedrock.contracts import Message
        from bedrock.models import ModelRequest

        messages = [
            Message(role="system", content=f"You are {identity.get('role', 'an agent')}."),
            Message(role="user", content=f"Input: {context.metadata.get('input', '')}\nDecide next action."),
        ]

        request = ModelRequest(messages=messages, temperature=0.3, max_tokens=256)
        response = await self.model_router.invoke("reasoning", request)

        text = response.content.strip().lower()
        if text.startswith("tool:"):
            parts = text.split(" ", 1)
            tool_name = parts[1] if len(parts) > 1 else "noop"
            return Decision(type=DecisionType.TOOL, tool_call=ToolCall(tool=tool_name))
        if text.startswith("final:"):
            content = text.split(":", 1)[1] if ":" in text else text
            return Decision(type=DecisionType.FINAL, final_output=FinalOutput(content=content.strip()))
        return Decision(type=DecisionType.NOOP)
