"""
Misconception detection: match a wrong answer against known error patterns.

meridian.persistence.models.learner.Misconception exists (concept_id,
name, signature, remediation) but nothing populated LearnerEvent.misconception_id
anywhere. This is the missing piece: a pure function matching an answer's
text against a concept's known misconceptions' signatures.

Deliberately keyword/regex matching, not an LLM classification call —
misconception signatures are hand-authored per concept (like the seeded
calculus DAG itself; see meridian/knowledge/seed_calculus.py's prototyping
note), so a learner's free-text or multiple-choice answer either contains
the pattern that names a known error or it doesn't. This keeps detection
synchronous, free, and testable without a model in the loop; an
LLM-classification fallback for answers that don't match any known
signature is a natural extension once a benchmark justifies its cost.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MisconceptionSpec:
    id: str
    concept_id: str
    name: str
    signature: str
    remediation: str = ""


def detect_misconception(
    answer_text: str, misconceptions: list[MisconceptionSpec]
) -> MisconceptionSpec | None:
    """Return the first misconception whose signature matches ``answer_text``.

    ``signature`` is treated as a case-insensitive regex; a plain keyword
    (no regex metacharacters) matches as a substring, which covers the
    common case without requiring every hand-authored signature to be
    regex-escaped. Returns None if nothing matches or ``answer_text`` is
    empty — an unmatched wrong answer is not itself a failure, just
    undiagnosed.
    """
    if not answer_text or not misconceptions:
        return None
    for misconception in misconceptions:
        if not misconception.signature:
            continue
        try:
            if re.search(misconception.signature, answer_text, re.IGNORECASE):
                return misconception
        except re.error:
            # A hand-authored signature that isn't valid regex still works
            # as a plain substring match rather than being silently skipped.
            if misconception.signature.lower() in answer_text.lower():
                return misconception
    return None
