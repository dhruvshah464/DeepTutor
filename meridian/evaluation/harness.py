"""
Evaluation harness: score a model's outputs against a set of cases.

Deliberately decoupled from any specific LLM call — ``model_fn`` is
injected, so the harness is fully testable offline with a fake model (see
tests/evaluation/test_harness.py) and only needs a real model_fn (backed
by meridian.bridge.engine.get_llm_client, or a specific provider via
deeptutor.services.llm.factory) wired in by the caller running an actual
benchmark. This is what "eval harness reproduces a scored run offline"
(ARCHITECTURE.md's Phase 3-5 verification) means: the harness's own
correctness doesn't depend on live API access, even though a real
benchmark run does.

No numbers from a benchmark are published anywhere in this repo until an
actual run exists to reproduce them — see README's metric-honesty rule.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
import time

ModelFn = Callable[[str], Awaitable[str]]
Scorer = Callable[["EvalCase", str], float]  # (case, actual_output) -> score in [0, 1]


@dataclass(frozen=True)
class EvalCase:
    id: str
    task_type: str  # "math" | "research" | "coding" | "socratic" | "vision", etc.
    prompt: str
    expected: str | None = None  # for scorers that need a reference answer
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EvalResult:
    case: EvalCase
    output: str
    score: float
    latency_ms: float
    error: str | None = None


@dataclass(frozen=True)
class EvalSummary:
    results: list[EvalResult]

    @property
    def mean_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def mean_latency_ms(self) -> float:
        successful = [r for r in self.results if r.error is None]
        if not successful:
            return 0.0
        return sum(r.latency_ms for r in successful) / len(successful)

    @property
    def error_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.error is not None) / len(self.results)

    def by_task_type(self) -> dict[str, "EvalSummary"]:
        groups: dict[str, list[EvalResult]] = {}
        for result in self.results:
            groups.setdefault(result.case.task_type, []).append(result)
        return {task_type: EvalSummary(results) for task_type, results in groups.items()}


def exact_match_scorer(case: EvalCase, output: str) -> float:
    if case.expected is None:
        raise ValueError(f"exact_match_scorer requires case.expected (case {case.id!r})")
    return 1.0 if output.strip() == case.expected.strip() else 0.0


def contains_scorer(case: EvalCase, output: str) -> float:
    if case.expected is None:
        raise ValueError(f"contains_scorer requires case.expected (case {case.id!r})")
    return 1.0 if case.expected.strip().lower() in output.lower() else 0.0


async def run_eval(
    cases: list[EvalCase],
    model_fn: ModelFn,
    scorer: Scorer,
    *,
    clock: Callable[[], float] = time.perf_counter,
) -> EvalSummary:
    """Run every case through ``model_fn``, score it, and summarize.

    A case that raises is recorded as an EvalResult with score=0.0 and
    ``error`` set, rather than aborting the whole run — one bad case
    shouldn't lose every other result in a long benchmark.
    """
    results: list[EvalResult] = []
    for case in cases:
        start = clock()
        try:
            output = await model_fn(case.prompt)
            latency_ms = (clock() - start) * 1000
            score = scorer(case, output)
            results.append(EvalResult(case=case, output=output, score=score, latency_ms=latency_ms))
        except Exception as exc:
            latency_ms = (clock() - start) * 1000
            results.append(
                EvalResult(case=case, output="", score=0.0, latency_ms=latency_ms, error=str(exc))
            )
    return EvalSummary(results)
