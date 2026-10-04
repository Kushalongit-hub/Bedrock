from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from bedrock.contracts import ToolCall, ToolResult


class ToolCapability(BaseModel):
    name: str
    risk: str = "low"
    permissions: Dict[str, Any] = Field(default_factory=dict)
    execution: Dict[str, Any] = Field(default_factory=dict)
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Optional[Dict[str, Any]] = None


class Tool(ABC):
    """Base contract for all tools in the system."""

    name: str
    capability: ToolCapability
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]]

    def __init__(self) -> None:
        if not hasattr(self, "name"):
            raise ValueError("Tool must define 'name'")
        self.input_schema = self.capability.input_schema
        self.output_schema = self.capability.output_schema

    @abstractmethod
    async def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        """Execute the tool with the given arguments and context."""
        ...

    async def validate_args(self, args: Dict[str, Any]) -> bool:
        """Validate tool arguments against schema (optional override)."""
        return True

    async def dry_run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Return a description of what the tool would do without executing."""
        return {"tool": self.name, "args": args, "preview": True}


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list(self) -> List[str]:
        return list(self._tools.keys())

    def all(self) -> Dict[str, Tool]:
        return dict(self._tools)

    def relevant(self, task: str, limit: int = 10) -> List[Tool]:
        """Return tools relevant to a given task (basic keyword matching)."""
        task_lower = task.lower()
        scored = []
        for tool in self._tools.values():
            score = 0
            if tool.name.lower() in task_lower:
                score += 10
            for kw in tool.name.split("."):
                if kw in task_lower:
                    score += 1
            scored.append((score, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:limit]]


class ToolExecutor:
    """Executes tool calls with policy enforcement."""

    def __init__(self, registry: ToolRegistry, policy: Any = None) -> None:
        self.registry = registry
        self.policy = policy

    async def execute(self, call: ToolCall, ctx: Any) -> ToolResult:
        tool = self.registry.get(call.tool)
        if tool is None:
            return ToolResult(
                call_id=call.call_id,
                tool=call.tool,
                success=False,
                error=f"Tool not found: {call.tool}",
            )

        if self.policy:
            allowed = await self.policy.check(call.tool, call.args, ctx)
            if not allowed:
                return ToolResult(
                    call_id=call.call_id,
                    tool=call.tool,
                    success=False,
                    error="Policy denied execution",
                )

        import time
        start = time.perf_counter()
        try:
            output = await tool.execute(ctx, call.args)
            duration = (time.perf_counter() - start) * 1000
            return ToolResult(
                call_id=call.call_id,
                tool=call.tool,
                success=True,
                output=output,
                duration_ms=duration,
            )
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            return ToolResult(
                call_id=call.call_id,
                tool=call.tool,
                success=False,
                error=str(exc),
                duration_ms=duration,
            )
