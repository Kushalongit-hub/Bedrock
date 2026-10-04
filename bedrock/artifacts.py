from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from bedrock.contracts import AgentState, Decision, ToolCall, ToolResult
from bedrock.events import Event, EventLogger, EventType


class RunManifest(BaseModel):
    run_id: str
    session_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: Optional[bool] = None
    input: Any = None
    final_output: Any = None
    identity: Dict[str, Any] = Field(default_factory=dict)
    model_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    decisions: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)
    event_count: int = 0
    iterations: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RunArtifactStore:
    """Persists run artifacts to disk: manifest, events, tool calls, model calls, artifacts."""

    def __init__(self, base_dir: str = "runs") -> None:
        self.base_dir = Path(base_dir)
        self._current_run_id: Optional[str] = None
        self._run_dir: Optional[Path] = None
        self._event_logger = EventLogger()
        self._manifest = RunManifest(
            run_id="",
            session_id="",
            started_at=datetime.now(timezone.utc),
        )

    def start_run(self, run_id: str, session_id: str, input_data: Any, identity: Dict[str, Any]) -> None:
        self._current_run_id = run_id
        self._run_dir = self.base_dir / run_id
        self._run_dir.mkdir(parents=True, exist_ok=True)
        (self._run_dir / "artifacts").mkdir(exist_ok=True)

        self._manifest = RunManifest(
            run_id=run_id,
            session_id=session_id,
            started_at=datetime.now(timezone.utc),
            input=input_data,
            identity=identity,
        )

    def record_event(self, event: Event) -> None:
        self._event_logger.handle(event)

    def record_tool_call(self, call: ToolCall, result: ToolResult) -> None:
        self._manifest.tool_calls.append({
            "tool": call.tool,
            "args": call.args,
            "call_id": call.call_id,
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "duration_ms": result.duration_ms,
        })

    def record_model_call(self, request: Any, response: Any) -> None:
        self._manifest.model_calls.append({
            "model": response.model,
            "provider": response.provider,
            "finish_reason": response.finish_reason,
            "usage": response.usage,
            "request_messages": len(request.messages) if hasattr(request, "messages") else 0,
            "tool_calls_count": len(response.tool_calls),
        })

    def record_decision(self, decision: Decision, iteration: int) -> None:
        self._manifest.decisions.append({
            "iteration": iteration,
            "type": decision.type.value,
            "tool_call": decision.tool_call.model_dump() if decision.tool_call else None,
            "final_output": decision.final_output.model_dump() if decision.final_output else None,
            "thought": decision.thought,
        })

    def record_artifact(self, name: str, content: Any) -> Optional[str]:
        if self._run_dir is None:
            return None
        artifacts_dir = self._run_dir / "artifacts"
        artifact_path = artifacts_dir / name
        if isinstance(content, str):
            artifact_path.write_text(content, encoding="utf-8")
        else:
            artifact_path.write_text(json.dumps(content, default=str, indent=2), encoding="utf-8")
        self._manifest.artifacts.append(name)
        return str(artifact_path)

    def complete_run(self, success: bool, final_output: Any, iterations: int) -> None:
        self._manifest.completed_at = datetime.now(timezone.utc)
        self._manifest.success = success
        self._manifest.final_output = final_output
        self._manifest.iterations = iterations
        self._manifest.event_count = len(self._event_logger.events)

        if self._run_dir is not None:
            manifest_path = self._run_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(self._manifest.model_dump(mode="json"), default=str, indent=2),
                encoding="utf-8",
            )

            events_path = self._run_dir / "events.jsonl"
            events_path.write_text(self._event_logger.to_jsonl(), encoding="utf-8")

    def get_run_dir(self, run_id: str) -> Optional[Path]:
        run_dir = self.base_dir / run_id
        return run_dir if run_dir.exists() else None

    def load_manifest(self, run_id: str) -> Optional[RunManifest]:
        run_dir = self.get_run_dir(run_id)
        if run_dir is None:
            return None
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.exists():
            return None
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return RunManifest(**data)

    def load_events(self, run_id: str) -> List[Event]:
        run_dir = self.get_run_dir(run_id)
        if run_dir is None:
            return []
        events_path = run_dir / "events.jsonl"
        if not events_path.exists():
            return []
        events = []
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                data = json.loads(line)
                events.append(Event(**data))
        return events


class RunReplayEngine:
    """Reconstructs a run from persisted artifacts."""

    def __init__(self, artifact_store: RunArtifactStore) -> None:
        self.artifact_store = artifact_store

    def replay(self, run_id: str) -> Dict[str, Any]:
        manifest = self.artifact_store.load_manifest(run_id)
        events = self.artifact_store.load_events(run_id)

        if manifest is None:
            return {"error": f"Run not found: {run_id}"}

        return {
            "run_id": run_id,
            "session_id": manifest.session_id,
            "started_at": manifest.started_at.isoformat(),
            "completed_at": manifest.completed_at.isoformat() if manifest.completed_at else None,
            "success": manifest.success,
            "input": manifest.input,
            "final_output": manifest.final_output,
            "iterations": manifest.iterations,
            "event_count": len(events),
            "tool_calls": manifest.tool_calls,
            "model_calls": manifest.model_calls,
            "decisions": manifest.decisions,
            "artifacts": manifest.artifacts,
            "events": [e.model_dump(mode="json") for e in events],
        }

    def replay_timeline(self, run_id: str) -> List[Dict[str, Any]]:
        events = self.artifact_store.load_events(run_id)
        timeline = []
        for event in events:
            entry = {
                "timestamp": event.timestamp.isoformat(),
                "type": event.type.value,
                "run_id": event.run_id,
                "step_id": event.step_id,
                "data": event.data,
            }
            timeline.append(entry)
        return timeline
