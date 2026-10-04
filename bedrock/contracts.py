from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class DecisionType(str, Enum):
    TOOL = "tool"
    FINAL = "final"
    PLAN = "plan"
    REPLAN = "replan"
    HUMAN = "human"
    ROUTE = "route"
    NOOP = "noop"


class ToolCall(BaseModel):
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    call_id: Optional[str] = None


class ToolResult(BaseModel):
    call_id: Optional[str] = None
    tool: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


class FinalOutput(BaseModel):
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlanStep(BaseModel):
    id: str
    description: str
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    status: str = "pending"


class Plan(BaseModel):
    steps: List[PlanStep] = Field(default_factory=list)
    thought: Optional[str] = None


class Decision(BaseModel):
    type: DecisionType
    tool_call: Optional[ToolCall] = None
    final_output: Optional[FinalOutput] = None
    plan: Optional[Plan] = None
    route_to: Optional[str] = None
    thought: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    session_id: str
    input: Any = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    current_step: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
