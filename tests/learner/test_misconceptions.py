from __future__ import annotations

from meridian.learner.misconceptions import MisconceptionSpec, detect_misconception


def _sign_error_misconception() -> MisconceptionSpec:
    return MisconceptionSpec(
        id="m1",
        concept_id="derivatives",
        name="Sign error on the power rule",
        signature=r"forgot.*(sign|negative)",
        remediation="Review how the power rule handles negative exponents.",
    )


def test_detect_misconception_matches_a_regex_signature():
    misconception = _sign_error_misconception()
    result = detect_misconception("I forgot the negative sign in the exponent", [misconception])
    assert result is misconception


def test_detect_misconception_is_case_insensitive():
    misconception = _sign_error_misconception()
    result = detect_misconception("I FORGOT THE NEGATIVE SIGN", [misconception])
    assert result is misconception


def test_detect_misconception_returns_none_when_nothing_matches():
    misconception = _sign_error_misconception()
    result = detect_misconception("the derivative of x^2 is 2x", [misconception])
    assert result is None


def test_detect_misconception_returns_none_for_empty_answer():
    misconception = _sign_error_misconception()
    assert detect_misconception("", [misconception]) is None


def test_detect_misconception_returns_none_without_any_misconceptions():
    assert detect_misconception("some answer", []) is None


def test_detect_misconception_falls_back_to_substring_for_invalid_regex():
    # An unescaped "(" makes this an invalid regex; must still match as a
    # plain substring rather than raising or silently never matching.
    broken = MisconceptionSpec(
        id="m2", concept_id="calculus", name="broken pattern", signature="f(x"
    )
    assert detect_misconception("I wrote f(x incorrectly", [broken]) is broken
    assert detect_misconception("no match here", [broken]) is None


def test_detect_misconception_returns_the_first_match_among_several():
    first = MisconceptionSpec(id="m1", concept_id="c", name="first", signature="alpha")
    second = MisconceptionSpec(id="m2", concept_id="c", name="second", signature="beta")
    result = detect_misconception("alpha and beta both appear", [first, second])
    assert result is first
