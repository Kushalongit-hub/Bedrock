from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from bedrock.memory import MemoryEntry, MemoryStore


class InMemoryStore(MemoryStore):
    """Simple in-memory store for development and testing."""

    def __init__(self) -> None:
        self._entries: Dict[str, MemoryEntry] = {}

    async def write(self, entry: MemoryEntry) -> str:
        if not entry.id:
            entry.id = str(uuid.uuid4())[:8]
        self._entries[entry.id] = entry
        return entry.id

    async def read(self, memory_id: str) -> Optional[MemoryEntry]:
        return self._entries.get(memory_id)

    async def search(
        self,
        query: str,
        memory_class: Optional[str] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        query_lower = query.lower()
        scored = []
        for entry in self._entries.values():
            if memory_class and entry.memory_class != memory_class:
                continue
            score = 0
            content = str(entry.content).lower()
            if query_lower in content:
                score += 10
            for tag in entry.tags:
                if tag.lower() in query_lower:
                    score += 1
            scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    async def delete(self, memory_id: str) -> bool:
        return self._entries.pop(memory_id, None) is not None

    async def clear(self, memory_class: Optional[str] = None) -> int:
        if memory_class is None:
            count = len(self._entries)
            self._entries.clear()
            return count
        to_delete = [eid for eid, e in self._entries.items() if e.memory_class == memory_class]
        for eid in to_delete:
            del self._entries[eid]
        return len(to_delete)
