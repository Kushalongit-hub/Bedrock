from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from bedrock.contracts import AgentState, Message
from bedrock.memory import MemoryEntry


class ContextBudget(BaseModel):
    max_tokens: int = 16000
    reserved_system: int = 2000
    reserved_tools: int = 2000
    reserved_output: int = 1000

    @property
    def available(self) -> int:
        return self.max_tokens - self.reserved_system - self.reserved_tools - self.reserved_output


class CompiledContext(BaseModel):
    system: str = ""
    messages: List[Message] = Field(default_factory=list)
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    memories: List[MemoryEntry] = Field(default_factory=list)
    knowledge: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextCompiler:
    """Compiles raw state into model-ready context."""

    def __init__(self, budget: Optional[ContextBudget] = None) -> None:
        self.budget = budget or ContextBudget()

    async def compile(
        self,
        identity: Dict[str, Any],
        state: AgentState,
        memories: List[MemoryEntry] = None,
        knowledge: List[Dict[str, Any]] = None,
        available_tools: List[Any] = None,
        token_budget: Optional[int] = None,
    ) -> CompiledContext:
        budget = token_budget or self.budget.available
        context = CompiledContext()

        context.system = self._build_system(identity, state)
        context.messages = state.history[-20:]
        context.memories = list(memories or [])[:5]
        context.knowledge = list(knowledge or [])[:3]

        tool_descriptions = []
        if available_tools:
            for tool in available_tools[:10]:
                tool_descriptions.append({
                    "name": tool.name,
                    "description": tool.capability.name,
                    "input_schema": tool.input_schema,
                })
        context.tools = tool_descriptions

        return context

    def _build_system(self, identity: Dict[str, Any], state: AgentState) -> str:
        parts = []
        if identity.get("role"):
            parts.append(f"You are {identity['role']}.")
        if identity.get("objective"):
            parts.append(f"Objective: {identity['objective']}.")
        if identity.get("style"):
            parts.append(f"Style: {identity['style']}.")
        if identity.get("constraints"):
            for k, v in identity["constraints"].items():
                parts.append(f"Constraint: {k} = {v}.")
        return "\n\n".join(parts) or "You are an autonomous agent."


class ContextSelector:
    """Selects relevant context for a given task."""

    async def select(
        self,
        state: AgentState,
        task: str,
        memories: List[MemoryEntry],
        knowledge: List[Dict[str, Any]],
        available_tools: List[Any],
        budget: int,
    ) -> Dict[str, Any]:
        return {
            "memories": memories[:5],
            "knowledge": knowledge[:3],
            "tools": available_tools[:10],
        }
