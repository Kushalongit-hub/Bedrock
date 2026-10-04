from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from bedrock.contracts import AgentState, Decision, ToolCall, ToolResult
from bedrock.events import Event, EventBus, EventType


class StepType(str, Enum):
    LLM = "model"
    CODE = "code"
    RULE = "rule"
    HUMAN = "human"
    TOOL = "tool"
    ROUTER = "router"
    VALIDATOR = "validator"
    RETRIEVER = "retriever"


class WorkflowStep(BaseModel):
    id: str
    type: StepType
    config: Dict[str, Any] = Field(default_factory=dict)
    input: Optional[str] = None
    output: Optional[str] = None
    on_error: Optional[str] = None
    retries: int = 0


class WorkflowDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    inputs: Dict[str, str] = Field(default_factory=dict)
    steps: List[WorkflowStep] = Field(default_factory=list)
    edges: List[Dict[str, str]] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    workflow_name: str
    success: bool
    outputs: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    events: List[Event] = Field(default_factory=list)


class WorkflowExecutor(ABC):
    """Base contract for workflow execution backends."""

    @abstractmethod
    async def execute(
        self,
        definition: WorkflowDefinition,
        state: AgentState,
        event_bus: EventBus,
        **kwargs: Any,
    ) -> WorkflowResult:
        ...


class SimpleWorkflowExecutor(WorkflowExecutor):
    """Sequential workflow executor."""

    async def execute(
        self,
        definition: WorkflowDefinition,
        state: AgentState,
        event_bus: EventBus,
        **kwargs: Any,
    ) -> WorkflowResult:
        result = WorkflowResult(workflow_name=definition.name, success=True)
        outputs: Dict[str, Any] = {}

        await event_bus.emit(Event(type=EventType.WORKFLOW_STARTED, data={"name": definition.name}))

        for step in definition.steps:
            try:
                step_result = await self._execute_step(step, state, kwargs)
                if step.output and step_result is not None:
                    outputs[step.output] = step_result
                await event_bus.emit(
                    Event(type=EventType.WORKFLOW_STEP_COMPLETED, data={"step": step.id, "success": True})
                )
            except Exception as exc:
                result.errors.append(f"{step.id}: {exc}")
                result.success = False
                if step.on_error:
                    break

        result.outputs = outputs
        await event_bus.emit(
            Event(
                type=EventType.WORKFLOW_COMPLETED if result.success else EventType.RUN_FAILED,
                data={"name": definition.name, "success": result.success},
            )
        )
        return result

    async def _execute_step(self, step: WorkflowStep, state: AgentState, kwargs: Dict[str, Any]) -> Any:
        handler = kwargs.get("step_handlers", {}).get(step.type)
        if handler is None:
            raise ValueError(f"No handler for step type: {step.type}")
        return await handler(step, state, kwargs)
