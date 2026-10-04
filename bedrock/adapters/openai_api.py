from __future__ import annotations

from typing import Any, Dict, List, Optional

from bedrock.adapters.fastapi_app import ChatRequest, ChatResponse, create_app


def create_openai_adapter(runtime: Any) -> Any:
    """Create an OpenAI-compatible API adapter.

    This retains the OpenAI chat semantics as ONE adapter,
    not the architecture itself.
    """
    return create_app(runtime=runtime)
