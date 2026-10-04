from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from bedrock.models import ModelProvider, ModelRequest, ModelResponse, TokenUsage


class OpenAICompatibleProvider(ModelProvider):
    """Provider for OpenAI-compatible APIs."""

    name: str = "openai_compatible"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(self, request: ModelRequest) -> ModelResponse:
        payload: Dict[str, Any] = {
            "model": request.model or self.model,
            "messages": [{"role": m.role.value, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.stop:
            payload["stop"] = request.stop
        if request.tools:
            payload["tools"] = request.tools

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})
        return ModelResponse(
            content=choice["message"].get("content", ""),
            model=data.get("model", self.model),
            provider=self.name,
            finish_reason=choice.get("finish_reason", "stop"),
            tool_calls=choice["message"].get("tool_calls", []),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            metadata={"raw": data},
        )


class AnthropicProvider(ModelProvider):
    """Provider for Anthropic Claude."""

    name: str = "anthropic"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-haiku-20241022",
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model

    async def generate(self, request: ModelRequest) -> ModelResponse:
        messages = []
        system_prompt = ""
        for m in request.messages:
            if m.role.value == "system":
                system_prompt = m.content
            else:
                messages.append({"role": m.role.value, "content": m.content})

        payload: Dict[str, Any] = {
            "model": request.model or self.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if request.tools:
            payload["tools"] = request.tools

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = ""
        tool_calls = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append({
                    "id": block.get("id"),
                    "name": block.get("name"),
                    "input": block.get("input", {}),
                })

        usage = data.get("usage", {})
        return ModelResponse(
            content=content,
            model=data.get("model", self.model),
            provider=self.name,
            finish_reason=data.get("stop_reason", "end_turn"),
            tool_calls=tool_calls,
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            },
            metadata={"raw": data},
        )


class EchoProvider(ModelProvider):
    """Testing provider that echoes the last user message."""

    name: str = "echo"

    async def generate(self, request: ModelRequest) -> ModelResponse:
        last_user = ""
        for m in reversed(request.messages):
            if m.role.value == "user":
                last_user = m.content
                break
        return ModelResponse(
            content=f"[echo] {last_user}",
            model="echo",
            provider=self.name,
            finish_reason="stop",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )
