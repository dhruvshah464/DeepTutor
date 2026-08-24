<div align="center">

<img src="assets/logo-ver2.png" alt="Meridian" width="160" style="border-radius: 20px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);">

# Meridian: Agentic Learning OS (built on DeepTutor)

<br/>

[![Built on](https://img.shields.io/badge/Built%20on-DeepTutor%20(HKUDS)-000000?style=flat-square)](https://github.com/HKUDS/DeepTutor)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue?style=flat-square)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

[Attribution](./ATTRIBUTION.md) · [Architecture](./ARCHITECTURE.md) · [What's Original](#whats-original-here) · [Roadmap](./docs/roadmap.md)
<br/>

</div>

---

## What this is

**Meridian** is an agentic learning OS built on top of the open-source
[DeepTutor](https://github.com/HKUDS/DeepTutor) tutoring engine (HKUDS,
Apache License 2.0). DeepTutor provides RAG-based document Q&A, multi-agent
problem solving, deep research pipelines, and a persistent TutorBot agent
system — none of which was written by this fork.

Meridian adds, as original work in the `meridian/` package:

- **A learner digital twin** — a Beta-Bernoulli mastery model per concept,
  with time-decay ("forgetting") and confidence derived from posterior
  variance, plus a prerequisite concept DAG used to diagnose *why* a learner
  is stuck, not just *what* they got wrong.
- **An adaptive curriculum planner** — schedules what to teach next as a
  constrained topological sort over the concept DAG, weighted by mastery
  deficit, decay urgency, and available time.
- **A production auth/tenancy/billing layer** on top of DeepTutor's engine
  (JWT auth, org-scoped multi-tenancy, Stripe billing scaffolding, quota
  enforcement) — see [ATTRIBUTION.md](./ATTRIBUTION.md) for exactly what
  was fixed and what remains a known gap.
- **An LLM evaluation lab and model router**, built on DeepTutor's existing
  provider-abstraction chokepoint, with real usage/cost capture instead of
  a word-count heuristic, and a model metadata catalog replacing three
  previously-divergent hardcoded pricing tables.
- **Real observability**: a contextvars-propagated span model with
  duration and parent-child tracking (what the engine's own trace-metadata
  plumbing isn't), wired into the one chokepoint every turn passes through
  regardless of capability; an error-rate tracker that finally receives
  real production traffic instead of none; a dead event bus repurposed
  with bounded backpressure and an actual subscriber.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the directory-level boundary
between inherited and original code, and [ATTRIBUTION.md](./ATTRIBUTION.md)
for the full inherited-vs-original breakdown with line counts, commit
references, and a per-module table of what exists and what's tested.

**No performance, scale, or accuracy claims are made here that have not
been measured in this repository.** The one class of claim reproduced on
demand is test counts: `pytest -q` — 294 passing (up from a 188-passing
baseline), 15 known pre-existing failures unrelated to this fork's changes
(see `ATTRIBUTION.md`'s baseline-triage section for what those are and why).
No benchmark numbers, latency figures, or a published model-routing table
exist yet — those require a live LLM provider this build environment
doesn't have; the harness and router that would produce them are built and
tested against a fake model instead of claimed as already run.

## What's original here

This fork's history is 505 commits, of which 2 are authored by
`dhruvshah464`; everything else is upstream DeepTutor history, preserved
intact (`git shortlog -sne`). The original work is:

1. `meridian/platform/` — auth, tenancy, rate limiting (moved from
   `deeptutor/auth/`, `deeptutor/security/`)
2. `meridian/persistence/` — ORM models, engine, Alembic migrations (moved
   from `deeptutor/database/`)
3. `meridian/api/` — the SaaS router surface (moved from
   `deeptutor/api/routers/`)
4. `meridian/learner/`, `meridian/knowledge/` — the digital twin (new)
5. `meridian/curriculum/` — the adaptive planner (new)
6. `meridian/evaluation/` — eval lab and model router (new)
7. `meridian/observability/` — tracing and usage accounting (new)
8. `meridian/bridge/` — the single seam through which `meridian/` calls
   into the inherited `deeptutor/` engine

Everything else — the RAG pipeline, the multi-agent solver, the research
pipeline, TutorBot, the CLI, and most of the frontend — is the inherited
DeepTutor engine, used as a dependency rather than rewritten. Treat
`deeptutor/` as a vendored subsystem: read `ATTRIBUTION.md` before assuming
any given file in this repo is original work.

---

## Architecture at a glance

```
meridian/                  ← original work (this fork)
  platform/                ← auth, tenancy, billing, ratelimit
  persistence/              ← ORM models, engine, migrations
  api/                      ← SaaS routers
  learner/                  ← digital twin: mastery, misconceptions
  knowledge/                ← concept graph, prerequisite DAG
  curriculum/                ← adaptive planner
  evaluation/                ← eval lab, benchmarks, model router
  observability/             ← spans, usage capture, cost accounting
  bridge/                    ← the only module that imports deeptutor.*

deeptutor/                  ← inherited DeepTutor engine (HKUDS, Apache 2.0)
  agents/                    ← multi-agent solve/research/question/guide
  core/                      ← stream bus, capability/tool registries
  services/                  ← LLM provider factory, session, memory, RAG
  tutorbot/                  ← persistent TutorBot agents
```

`meridian/` code is only allowed to import `deeptutor/` through
`meridian/bridge/` — one seam, one place to swap the engine. See
[ARCHITECTURE.md](./ARCHITECTURE.md) for the full rationale and the phased
roadmap that got here.

---

## Running it locally

```bash
git clone https://github.com/dhruvshah464/DeepTutor.git
cd DeepTutor
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
cp .env.example .env   # fill in LLM/embedding keys

# Backend
uvicorn deeptutor.api.main:app --reload --port 8001

# Frontend
cd web && npm install && npm run dev
```

For Docker Compose and production deployment notes, see
`docker-compose.yml` / `docker-compose.ghcr.yml`.

## CLI

```bash
deeptutor run deep_solve "Compute the Fourier Transform eigenvalues" -t reason
deeptutor kb create advanced_physics --doc tensor_calculus.pdf
deeptutor session list
deeptutor bot create mr-miyagi --persona "Philosophical, concise, relies on first principles"
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). Issues and PRs for the
`meridian/` layer belong on this fork; issues in the inherited engine
itself are often better filed upstream at
[HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor).

## License

Apache License 2.0 — see [LICENSE](./LICENSE) and [NOTICE](./NOTICE).
