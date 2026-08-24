# Architecture

This document describes the boundary between inherited and original code in
this repository, why it's drawn where it is, and the phased plan that
produced it. It complements [ATTRIBUTION.md](./ATTRIBUTION.md) (what is
whose) with the structural rationale (how the two halves fit together).

## The boundary is physical, not aspirational

```
meridian/                  ← ALL original work
  platform/                ← auth, tenancy, billing, ratelimit  (moved from deeptutor/)
  persistence/              ← ORM models, engine, migrations     (moved from deeptutor/database/)
  api/                       ← SaaS routers                       (moved from deeptutor/api/routers/)
  learner/                   ← digital twin: mastery, misconceptions
  knowledge/                 ← concept graph, prerequisite DAG
  curriculum/                ← adaptive planner
  assessment/                 ← diagnosis, difficulty adaptation
  evaluation/                 ← eval lab, benchmarks, model router
  observability/              ← spans, usage capture, cost accounting
  bridge/                     ← the only module that imports deeptutor.*

deeptutor/                  ← INHERITED engine, treated as a dependency
```

**Rule: `meridian/` imports `deeptutor/` only through `meridian/bridge/`.**
Everything Meridian needs from the inherited engine — turn execution,
session lookups, agent invocation, the LLM factory — goes through a bridge
module that wraps the corresponding `deeptutor.*` call. This buys three
things:

1. **Legibility.** A reviewer (or interviewer) can look at the directory
   tree and immediately see what's original: `meridian/*` minus `bridge/`
   internals. No file-by-file archaeology required.
2. **One seam to swap the engine.** If DeepTutor's internals change, or a
   different engine is substituted entirely, only `meridian/bridge/` needs
   to change — not the learner model, planner, or evaluation lab.
3. **Minimal, reversible touches to `deeptutor/`.** Where Meridian needs the
   engine to do something new (e.g. mirror a turn to Postgres), the change
   is a small, non-fatal hook inside `deeptutor/`, not a rewrite. See
   "Hook pattern" below.

## Data flow: the closed loop

```
interaction → learner state → diagnosis → strategy → response → assessment → state update → replan
```

1. A learner interacts with a DeepTutor agent (chat, solve, guide, question)
   through the existing `TurnRuntimeManager`.
2. `_persist_and_publish` (`deeptutor/services/session/turn_runtime.py`)
   fires a non-fatal hook that mirrors the turn into Postgres
   (`ChatSession`/`ChatMessage`) and, via `meridian/bridge/`, emits
   `LearnerEvent`s tagged with concept, correctness, difficulty, and
   latency.
3. `meridian/learner/mastery.py` updates the Beta-Bernoulli
   `LearnerConceptState` for each tagged concept — pure function, no LLM.
4. `meridian/knowledge/diagnosis.py` walks the prerequisite DAG from a
   target concept to the weakest upstream node with insufficient mastery.
5. `meridian/curriculum/planner.py` produces or invalidates a schedule
   based on the updated state.
6. The next response is shaped by that plan; the loop repeats.

Everything left of step 2 is inherited DeepTutor. Everything from step 2
onward is original.

## Hook pattern: non-fatal, additive, reversible

Modeled on the engine's own `_mirror_event_to_workspace`
(`deeptutor/services/session/turn_runtime.py`): a static method wrapped in
try/except that logs and swallows failures rather than failing the turn.
Meridian's Postgres-mirror and learner-event hooks follow the same shape —
a bug in Meridian's bookkeeping must never break a tutoring turn. This is
also why these hooks live as thin call-outs inside `deeptutor/`, rather than
DeepTutor being restructured to depend on Meridian: the dependency
direction stays `meridian → deeptutor`, never the reverse.

## Why the engine isn't rewritten

The inherited engine (RAG ingestion, multi-agent solve/research, the
provider-abstraction chokepoint in `deeptutor/services/llm/factory.py`,
`BaseAgent`, `StreamBus`) is already well-designed in the places Meridian
needs to extend it — see the routing insertion point and provider-registry
notes in `meridian/evaluation/`. Rewriting it would trade a real, working
system for a rewrite risk with no corresponding gain; the original
contribution here is the learner-modeling and planning layer the engine
never had, not a re-implementation of RAG or multi-agent orchestration.

## Phased build order

Each phase is independently shippable and demoable; later phases depend on
earlier ones being real (Phase 3's replanning needs Phase 2's mastery
updates; Phase 6 composes 2 through 5).

| Phase | Scope |
|---|---|
| 0 | Ownership & attribution fix; `meridian/` skeleton; CI restored |
| 1 | Close the SaaS layer's security holes; consolidate the data path; capture real usage |
| 2 | Learner digital twin — the differentiator |
| 3 | Adaptive curriculum planner |
| 4 | Evaluation lab & model router |
| 5 | Observability |
| 6 | Compose 2-5 into the "Learning Autopilot" demo; reproducible writeup |

See `ATTRIBUTION.md` for what each phase actually shipped versus what
remains a documented, known gap.
