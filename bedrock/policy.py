from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from bedrock.tools import ToolCapability, ToolCall


class PermissionRule(BaseModel):
    capability: Optional[str] = None
    allow: bool = True
    require_approval: bool = False
    max_risk: str = "medium"
    conditions: Dict[str, Any] = Field(default_factory=dict)


class PolicyEngine:
    """Enforces permissions and safety boundaries."""

    def __init__(self, rules: Optional[List[PermissionRule]] = None) -> None:
        self.rules = rules or []

    async def check(self, tool_name: str, args: Dict[str, Any], ctx: Any) -> bool:
        """Check if a tool call is allowed by policy."""
        for rule in self.rules:
            if rule.capability and not self._matches(rule.capability, tool_name):
                continue
            if not rule.allow:
                return False
            if rule.require_approval:
                return await self._request_approval(tool_name, args, ctx)
        return True

    def _matches(self, capability: str, tool_name: str) -> bool:
        return capability == tool_name or capability in tool_name

    async def _request_approval(self, tool_name: str, args: Dict[str, Any], ctx: Any) -> bool:
        """Request human approval (override in subclasses)."""
        return False

    def risk_level(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Return risk level for a tool call."""
        return "low"


class CapabilityManager:
    """Manages agent capabilities."""

    def __init__(self, granted: Optional[List[str]] = None) -> None:
        self.granted = set(granted or [])

    def has(self, capability: str) -> bool:
        return capability in self.granted

    def grant(self, capability: str) -> None:
        self.granted.add(capability)

    def revoke(self, capability: str) -> None:
        self.granted.discard(capability)

    def check(self, capability: str) -> bool:
        return self.has(capability)
