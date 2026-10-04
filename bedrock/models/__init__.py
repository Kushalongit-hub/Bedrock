from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from bedrock.contracts import Message, MessageRole


class ModelRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    stop: List[str] = Field(default_factory=list)
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelResponse(BaseModel):
    content: str
    model: str
    provider: str
    finish_reason: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    usage: Dict[str, int] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelProvider(ABC):
    """Base contract for model providers."""

    name: str

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        ...


class ModelRouter:
    """Routes model requests to appropriate providers."""

    def __init__(self, providers: Dict[str, ModelProvider], routes: Dict[str, str]) -> None:
        self._providers = providers
        self._routes = routes

    def resolve(self, alias: str) -> Optional[ModelProvider]:
        provider_name = self._routes.get(alias, alias)
        return self._providers.get(provider_name)

    async def invoke(self, alias: str, request: ModelRequest) -> ModelResponse:
        provider = self.resolve(alias)
        if provider is None:
            raise ValueError(f"No provider for model alias: {alias}")
        return await provider.generate(request)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )
