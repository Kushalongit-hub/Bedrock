from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from bedrock.contracts import AgentState
from bedrock.runtime import AgentRuntime
from bedrock.memory import MemorySystem
from bedrock.memory.stores import InMemoryStore
from bedrock.models import ModelRouter
from bedrock.models.providers import EchoProvider
from bedrock.tools import ToolExecutor, ToolRegistry


class ChatRequest(BaseModel):
    input: Any
    session_id: Optional[str] = "default"
    identity: Optional[Dict[str, Any]] = None
    expected: Optional[Any] = None


class ChatResponse(BaseModel):
    output: Any
    run_id: str
    iterations: int


def create_app(runtime: AgentRuntime) -> FastAPI:
    app = FastAPI(title="Bedrock Agent API")

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatRequest) -> ChatResponse:
        state = AgentState(session_id=request.session_id or "default", input=request.input)
        identity = request.identity or {}
        result = await runtime.run(state=state, identity=identity, expected=request.expected)
        final = result.artifacts.get("final", {})
        return ChatResponse(
            output=final.get("content") if final else None,
            run_id=result.metadata.get("run_id", ""),
            iterations=len(result.history),
        )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app
