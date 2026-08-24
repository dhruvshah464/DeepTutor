"""
Learner Digital Twin API Router
=================================

Read/query surface over the learner mastery model (meridian/learner/) and
concept graph (meridian/knowledge/). Original Meridian code — not
inherited from DeepTutor.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.knowledge.diagnosis import diagnose
from meridian.knowledge.graph import ConceptGraph
from meridian.learner.mastery import confidence as confidence_of
from meridian.learner.mastery import decay
from meridian.learner.service import get_mastery_map, record_event, state_from_row
from meridian.persistence.engine import get_db_session
from meridian.persistence.models.learner import Concept, ConceptEdge, LearnerConceptState
from meridian.platform.auth.dependencies import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


async def _load_graph_and_names(db: AsyncSession) -> tuple[ConceptGraph, dict[str, str], dict[str, str]]:
    """Build a ConceptGraph from the DB, keyed by concept id (not slug).

    Returns (graph, id_to_name, slug_to_id) — diagnosis operates on ids
    (stable across a rename), display uses names.
    """
    concepts = (await db.execute(select(Concept))).scalars().all()
    edges = (
        await db.execute(select(ConceptEdge).where(ConceptEdge.relation == "prerequisite"))
    ).scalars().all()

    graph = ConceptGraph()
    id_to_name: dict[str, str] = {}
    slug_to_id: dict[str, str] = {}
    for concept in concepts:
        graph.add_concept(concept.id)
        id_to_name[concept.id] = concept.name
        slug_to_id[concept.slug] = concept.id
    for edge in edges:
        graph.add_edge(edge.src_id, edge.dst_id, weight=edge.weight)

    return graph, id_to_name, slug_to_id


@router.get("/learner/mastery")
async def list_mastery(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Every concept's live mastery/confidence for the current user."""
    from datetime import datetime, timezone

    _graph, id_to_name, _slugs = await _load_graph_and_names(db)

    rows = (
        await db.execute(
            select(LearnerConceptState).where(LearnerConceptState.user_id == user["sub"])
        )
    ).scalars().all()

    now = datetime.now(timezone.utc)
    results = []
    for row in rows:
        state = decay(state_from_row(row), now)
        results.append(
            {
                "concept_id": row.concept_id,
                "concept_name": id_to_name.get(row.concept_id, row.concept_id),
                "mastery": round(state.alpha / (state.alpha + state.beta), 4),
                "confidence": round(confidence_of(state), 4),
                "evidence_count": state.evidence_count,
                "velocity": round(state.velocity, 4),
            }
        )
    return {"concepts": results}


@router.get("/learner/diagnose")
async def diagnose_gap(
    concept: str = Query(..., description="Concept slug the learner asked about"),
    threshold: float = Query(default=0.7, ge=0.0, le=1.0),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Walk the prerequisite DAG upstream from ``concept`` and name the weakest link.

    The headline demo behavior: given a question about one concept, this
    doesn't just report that concept's mastery — it finds the weakest
    prerequisite behind it, which is usually the concept actually worth
    teaching next.
    """
    graph, id_to_name, slug_to_id = await _load_graph_and_names(db)
    concept_id = slug_to_id.get(concept)
    if concept_id is None:
        raise HTTPException(status_code=404, detail=f"Unknown concept: {concept}")

    ancestor_ids = graph.prerequisites_of(concept_id, transitive=True) | {concept_id}
    mastery_map = await get_mastery_map(db, user_id=user["sub"], concept_ids=list(ancestor_ids))

    result = diagnose(concept_id, graph, mastery_map.get, threshold=threshold)
    if result is None:
        return {
            "target_concept": concept,
            "diagnosis": None,
            "message": "No gap found above the threshold on this concept's prerequisite chain.",
        }

    return {
        "target_concept": concept,
        "diagnosis": {
            "weak_concept_id": result.weak_concept_id,
            "weak_concept_name": id_to_name.get(result.weak_concept_id, result.weak_concept_id),
            "weak_mastery": round(result.weak_mastery, 4),
            "is_target_itself": result.is_target_itself,
            "chain": [
                {
                    "concept_id": cid,
                    "concept_name": id_to_name.get(cid, cid),
                    "mastery": round(score, 4),
                }
                for cid, score in zip(result.chain, result.chain_mastery)
            ],
        },
    }


@router.post("/learner/events")
async def record_learner_event(
    body: dict,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Record one graded interaction (quiz answer, flashcard review, etc).

    Body: {"concept": "<slug>", "correct": bool, "difficulty": float (0-1,
    default 0.5), "event_type": str (default "quiz"), "source_turn_id": str|None}

    This is the general-purpose entry point; meridian/api/learning.py's
    submit_quiz calls the same underlying meridian.learner.service.record_event
    directly for the quiz-grading path specifically, since it already has
    the concept/correctness data in hand.
    """
    concept_slug = body.get("concept")
    if not concept_slug:
        raise HTTPException(status_code=422, detail="Missing 'concept'")
    correct = bool(body.get("correct"))
    difficulty = float(body.get("difficulty", 0.5))

    concept = (
        await db.execute(select(Concept).where(Concept.slug == concept_slug))
    ).scalar_one_or_none()
    if concept is None:
        raise HTTPException(status_code=404, detail=f"Unknown concept: {concept_slug}")

    state = await record_event(
        db,
        user_id=user["sub"],
        concept_id=concept.id,
        correct=correct,
        difficulty=difficulty,
        event_type=str(body.get("event_type", "quiz")),
        source_turn_id=body.get("source_turn_id"),
    )
    return {
        "concept_id": state.concept_id,
        "mastery": round(state.alpha / (state.alpha + state.beta), 4),
        "evidence_count": state.evidence_count,
    }
