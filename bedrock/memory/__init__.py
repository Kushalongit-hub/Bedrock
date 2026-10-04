from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryProvenance(BaseModel):
    source: str
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryEntry(BaseModel):
    id: str
    content: Any
    memory_class: str
    provenance: MemoryProvenance
    tags: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None


class MemoryStore(ABC):
    """Base contract for memory stores."""

    @abstractmethod
    async def write(self, entry: MemoryEntry) -> str:
        """Write a memory entry, return its id."""
        ...

    @abstractmethod
    async def read(self, memory_id: str) -> Optional[MemoryEntry]:
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        memory_class: Optional[str] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        ...

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        ...

    @abstractmethod
    async def clear(self, memory_class: Optional[str] = None) -> int:
        """Clear memories, optionally filtered by class. Return count cleared."""
        ...


class WorkingMemory:
    """Current task and short-term scratchpad."""

    def __init__(self) -> None:
        self.task: Optional[str] = None
        self.step: Optional[str] = None
        self.scratchpad: Dict[str, Any] = {}
        self.budget_remaining: int = 0

    def reset(self) -> None:
        self.task = None
        self.step = None
        self.scratchpad = {}
        self.budget_remaining = 0


class SessionMemory:
    """Current conversation/run memory."""

    def __init__(self) -> None:
        self.turns: List[Dict[str, Any]] = []
        self.decisions: List[Dict[str, Any]] = []
        self.tool_calls: List[Dict[str, Any]] = []
        self.artifacts: Dict[str, Any] = {}

    def add_turn(self, turn: Dict[str, Any]) -> None:
        self.turns.append(turn)

    def add_decision(self, decision: Dict[str, Any]) -> None:
        self.decisions.append(decision)


class EpisodicMemory:
    """What happened previously — run history."""

    def __init__(self) -> None:
        self.runs: List[Dict[str, Any]] = []

    def record_run(self, run: Dict[str, Any]) -> None:
        self.runs.append(run)


class SemanticMemory:
    """Facts learned over time."""

    def __init__(self) -> None:
        self.facts: List[MemoryEntry] = []


class ProceduralMemory:
    """Successful methods and workflows."""

    def __init__(self) -> None:
        self.workflows: List[Dict[str, Any]] = []
        self.success_patterns: List[Dict[str, Any]] = []


class ArtifactMemory:
    """Code/docs/files created during runs."""

    def __init__(self) -> None:
        self.artifacts: Dict[str, MemoryEntry] = {}

    def register(self, name: str, entry: MemoryEntry) -> None:
        self.artifacts[name] = entry


class UserMemory:
    """User preferences, if product allows."""

    def __init__(self) -> None:
        self.preferences: Dict[str, Any] = {}
        self.constraints: List[str] = []


class MemorySystem:
    """Unified memory facade."""

    def __init__(
        self,
        store: MemoryStore,
    ) -> None:
        self.store = store
        self.working = WorkingMemory()
        self.session = SessionMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self.artifact = ArtifactMemory()
        self.user = UserMemory()

    async def remember(self, entry: MemoryEntry) -> str:
        return await self.store.write(entry)

    async def recall(
        self,
        query: str,
        memory_class: Optional[str] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        return await self.store.search(query, memory_class=memory_class, limit=limit)
