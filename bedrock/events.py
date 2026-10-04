from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"

    MODEL_CALLED = "model.called"
    MODEL_COMPLETED = "model.completed"
    MODEL_FAILED = "model.failed"

    TOOL_REQUESTED = "tool.requested"
    TOOL_AUTHORIZED = "tool.authorized"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    MEMORY_READ = "memory.read"
    MEMORY_WRITE = "memory.write"

    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_STEP_COMPLETED = "workflow.step.completed"

    POLICY_DENIED = "policy.denied"
    HUMAN_APPROVAL_REQUESTED = "human.approval.requested"
    HUMAN_APPROVAL_RECEIVED = "human.approval.received"

    AGENT_COMPLETED = "agent.completed"
    AGENT_ERROR = "agent.error"


class Event(BaseModel):
    type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    run_id: Optional[str] = None
    step_id: Optional[str] = None


EventHandler = Callable[[Event], None]


class EventBus:
    """In-process event bus for observability."""

    def __init__(self) -> None:
        self._handlers: List[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        self._handlers.remove(handler)

    async def emit(self, event: Event) -> None:
        for handler in self._handlers:
            handler(event)

    async def emit_async(self, event: Event) -> None:
        await self.emit(event)


class EventLogger:
    """Simple event logger that writes to a list (replay support)."""

    def __init__(self) -> None:
        self.events: List[Event] = []

    def handle(self, event: Event) -> None:
        self.events.append(event)

    def replay(self) -> List[Event]:
        return list(self.events)

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(e.model_dump(mode="json"), default=str) for e in self.events)
