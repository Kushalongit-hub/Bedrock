from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from bedrock.contracts import AgentState, Decision


class EvaluationResult(BaseModel):
    evaluator: str
    passed: bool
    score: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)


class Evaluator(ABC):
    """Base contract for run evaluators."""

    name: str

    @abstractmethod
    async def evaluate(
        self,
        state: AgentState,
        final_output: Any,
        expected: Optional[Any] = None,
    ) -> EvaluationResult:
        ...


class EvaluationRunner:
    """Runs evaluators against a completed run."""

    def __init__(self, evaluators: Optional[List[Evaluator]] = None) -> None:
        self.evaluators = evaluators or []

    async def run(
        self,
        state: AgentState,
        final_output: Any,
        expected: Optional[Any] = None,
    ) -> Dict[str, EvaluationResult]:
        results: Dict[str, EvaluationResult] = {}
        for evaluator in self.evaluators:
            result = await evaluator.evaluate(state, final_output, expected)
            results[evaluator.name] = result
        return results

    def summary(self, results: Dict[str, EvaluationResult]) -> Dict[str, float]:
        scores = {}
        for name, result in results.items():
            scores[name] = result.score if result.passed else 0.0
        return scores
