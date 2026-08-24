"""
Hand-authored prerequisite DAG for one domain (calculus -> ML optimization),
per ARCHITECTURE.md's risk note: "Concept tagging quality gates the whole
twin. Prototype on one domain (ML/calculus) with a hand-authored DAG before
attempting general extraction."

This is deliberately small and curated rather than generated — the point
of the prototype is to prove the mastery kernel + diagnosis loop on real,
correct domain structure before investing in automatic concept extraction
from arbitrary content.

Run as a script (`python -m meridian.knowledge.seed_calculus`) or import
`SEED_CONCEPTS`/`SEED_EDGES` directly for tests/demos that need the graph
without touching a database.
"""

from __future__ import annotations

from meridian.knowledge.graph import ConceptGraph

# (slug, name, domain, description)
SEED_CONCEPTS: list[tuple[str, str, str, str]] = [
    ("arithmetic", "Arithmetic", "calculus", "Basic numeric operations."),
    ("algebra", "Algebra", "calculus", "Variables, equations, and functions."),
    ("limits", "Limits", "calculus", "The behavior of a function as its input approaches a value."),
    ("calculus", "Calculus", "calculus", "Rates of change and accumulation."),
    ("derivatives", "Derivatives", "calculus", "The instantaneous rate of change of a function."),
    ("partial_derivatives", "Partial Derivatives", "calculus", "Derivatives with respect to one variable of a multivariable function."),
    ("gradients", "Gradients", "calculus", "The vector of partial derivatives; points in the direction of steepest ascent."),
    ("convexity", "Convexity", "calculus", "Whether a function curves upward everywhere, guaranteeing a single minimum."),
    ("optimization", "Optimization", "calculus", "Finding the input that minimizes or maximizes a function."),
    ("learning_rate", "Learning Rate", "calculus", "The step size hyperparameter in gradient-based optimization."),
    ("gradient_descent", "Gradient Descent", "calculus", "Iteratively stepping opposite the gradient to minimize a function."),
]

# (src=prerequisite, dst=dependent)
SEED_EDGES: list[tuple[str, str]] = [
    ("arithmetic", "algebra"),
    ("algebra", "limits"),
    ("limits", "calculus"),
    ("calculus", "derivatives"),
    ("derivatives", "partial_derivatives"),
    ("partial_derivatives", "gradients"),
    ("derivatives", "convexity"),
    ("gradients", "optimization"),
    ("convexity", "optimization"),
    ("optimization", "learning_rate"),
    ("learning_rate", "gradient_descent"),
]


def build_graph() -> ConceptGraph:
    """The seed DAG as an in-memory ConceptGraph, keyed by slug (no DB needed)."""
    graph = ConceptGraph()
    for slug, *_ in SEED_CONCEPTS:
        graph.add_concept(slug)
    for src, dst in SEED_EDGES:
        graph.add_edge(src, dst)
    return graph


def concept_names() -> dict[str, str]:
    return {slug: name for slug, name, _domain, _desc in SEED_CONCEPTS}


async def seed_database() -> None:
    """Upsert SEED_CONCEPTS/SEED_EDGES into Postgres. Idempotent."""
    from sqlalchemy import select

    from meridian.persistence.engine import get_async_session
    from meridian.persistence.models.learner import Concept, ConceptEdge

    async with get_async_session() as db:
        slug_to_id: dict[str, str] = {}
        for slug, name, domain, description in SEED_CONCEPTS:
            existing = (
                await db.execute(select(Concept).where(Concept.slug == slug))
            ).scalar_one_or_none()
            if existing is None:
                concept = Concept(slug=slug, name=name, domain=domain, description=description)
                db.add(concept)
                await db.flush()
                slug_to_id[slug] = concept.id
            else:
                slug_to_id[slug] = existing.id

        for src_slug, dst_slug in SEED_EDGES:
            src_id, dst_id = slug_to_id[src_slug], slug_to_id[dst_slug]
            existing_edge = (
                await db.execute(
                    select(ConceptEdge).where(
                        ConceptEdge.src_id == src_id,
                        ConceptEdge.dst_id == dst_id,
                        ConceptEdge.relation == "prerequisite",
                    )
                )
            ).scalar_one_or_none()
            if existing_edge is None:
                db.add(ConceptEdge(src_id=src_id, dst_id=dst_id, relation="prerequisite"))


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_database())
    print(f"Seeded {len(SEED_CONCEPTS)} concepts and {len(SEED_EDGES)} edges.")
