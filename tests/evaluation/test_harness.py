from __future__ import annotations

import pytest

from meridian.evaluation.harness import (
    EvalCase,
    contains_scorer,
    exact_match_scorer,
    run_eval,
)


async def _fake_model(prompt: str) -> str:
    responses = {
        "2+2": "4",
        "capital of France": "The capital of France is Paris.",
    }
    return responses.get(prompt, "I don't know")


async def _always_failing_model(prompt: str) -> str:
    raise RuntimeError("provider timeout")


@pytest.mark.asyncio
async def test_run_eval_scores_each_case_with_exact_match():
    cases = [EvalCase(id="c1", task_type="math", prompt="2+2", expected="4")]

    summary = await run_eval(cases, _fake_model, exact_match_scorer)

    assert summary.mean_score == 1.0
    assert summary.error_rate == 0.0
    assert summary.results[0].latency_ms >= 0


@pytest.mark.asyncio
async def test_run_eval_with_contains_scorer_for_free_text_answers():
    cases = [
        EvalCase(id="c1", task_type="research", prompt="capital of France", expected="Paris")
    ]

    summary = await run_eval(cases, _fake_model, contains_scorer)

    assert summary.mean_score == 1.0


@pytest.mark.asyncio
async def test_run_eval_scores_wrong_answers_as_zero_not_an_error():
    cases = [EvalCase(id="c1", task_type="math", prompt="2+2", expected="5")]

    summary = await run_eval(cases, _fake_model, exact_match_scorer)

    assert summary.mean_score == 0.0
    assert summary.error_rate == 0.0
    assert summary.results[0].error is None


@pytest.mark.asyncio
async def test_run_eval_records_model_errors_without_aborting_the_run():
    cases = [
        EvalCase(id="fails", task_type="math", prompt="2+2", expected="4"),
        EvalCase(id="succeeds", task_type="math", prompt="2+2", expected="4"),
    ]

    call_count = 0

    async def flaky(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("provider timeout")
        return "4"

    summary = await run_eval(cases, flaky, exact_match_scorer)

    assert len(summary.results) == 2
    assert summary.results[0].error == "provider timeout"
    assert summary.results[0].score == 0.0
    assert summary.results[1].error is None
    assert summary.results[1].score == 1.0
    assert summary.error_rate == 0.5


@pytest.mark.asyncio
async def test_by_task_type_groups_results_for_per_domain_reporting():
    cases = [
        EvalCase(id="m1", task_type="math", prompt="2+2", expected="4"),
        EvalCase(id="r1", task_type="research", prompt="capital of France", expected="Paris"),
    ]

    summary = await run_eval(cases, _fake_model, contains_scorer)
    grouped = summary.by_task_type()

    assert set(grouped.keys()) == {"math", "research"}
    assert grouped["math"].mean_score == 1.0
    assert grouped["research"].mean_score == 1.0


def test_exact_match_scorer_requires_an_expected_value():
    case = EvalCase(id="c1", task_type="math", prompt="2+2", expected=None)
    with pytest.raises(ValueError):
        exact_match_scorer(case, "4")
