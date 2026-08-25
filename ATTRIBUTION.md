# Attribution

This repository is a fork of [HKUDS/DeepTutor](https://github.com/HKUDS/DeepTutor)
(Apache License 2.0). This document states, as accurately as the git history
allows, what in this repository is inherited from upstream and what is
original work, per Apache 2.0 §4(b) ("state that... files... have been
modified") and §4(d) (NOTICE obligations).

## Headline numbers

- **505 commits** in this repository's history; **2** are authored by the
  fork's owner (`dhruvshah464`). Everything else is inherited upstream
  history. Verify with:
  ```
  git shortlog -sne
  ```
- The owner's largest commit, `d3abe6b` ("SaaS Architecture, Multi-Tenant
  Postgres, Stripe, Full Rewrite"), touches 76 files and adds **6,805**
  lines, against a codebase of roughly **103,000** lines at the time —
  **~6.6%** of the total. It is additive scaffolding (new auth, database,
  security, and API-router modules plus matching frontend pages); it does
  not rewrite the inherited RAG, multi-agent solving, or research engine.
- Prior README language claiming the platform was *"Engineered entirely
  from the ground up"* and *"procedurally synthesized... hundreds of
  thousands of lines"* was false and has been removed (see `README.md`
  history for the previous wording).

## What is inherited (upstream DeepTutor, unmodified in design)

| Path | Role |
|---|---|
| `deeptutor/agents/` | Multi-agent solving, research, question generation, guide/tutoring agents |
| `deeptutor/core/` | Runtime core: stream bus, tracing scaffolding, capability/tool registries |
| `deeptutor/services/llm/` | LLM provider factory, executors, provider registry |
| `deeptutor/services/session/`, `services/memory/` | Turn runtime, session state, memory (`SUMMARY.md`/`PROFILE.md`) |
| `deeptutor/knowledge/`, RAG ingestion paths | Document ingestion, embeddings, retrieval |
| `deeptutor/tutorbot/`, `deeptutor/tools/` | TutorBot persona/heartbeat system, atomic tools |
| `deeptutor_cli/` | CLI entrypoints |
| `web/app/(workspace)/{agents,guide,co-writer,playground}`, most of `web/components`, `web/lib` (pre-existing files) | Chat, solve, research, guided-canvas UI |
| `docs/` (VitePress site, feature docs) | Except contribution/community links corrected in Phase 0 |

This is the majority of the codebase by line count (roughly 93% of the
~103k-line baseline) and is **not original work of this fork**. Full credit
belongs to HKUDS and the upstream DeepTutor contributors:
https://github.com/HKUDS/DeepTutor/graphs/contributors.

## What is original (this fork, `dhruvshah464`)

From commit `d3abe6b`, ~6,805 lines / 76 files, ~3,500 LOC of which is
backend:

| Path | Role | Status as of Phase 0 |
|---|---|---|
| `deeptutor/auth/` (→ `meridian/platform/auth/`) | JWT auth, password hashing, permissions, dependencies | Real, but `get_ws_user` was unused and bcrypt was undeclared — fixed in Phase 1 |
| `deeptutor/database/` (→ `meridian/persistence/`) | SQLAlchemy models (user, org, billing, session, learning, knowledge, audit), engine, seed data | Real; no Alembic migration existed until Phase 1 |
| `deeptutor/security/` (→ `meridian/platform/security/`) | Rate limiter, security headers, audit logging | Real, narrow |
| `deeptutor/api/routers/{admin,analytics,auth,billing,health,learning,orgs}.py` (→ `meridian/api/`) | SaaS API surface | Written but largely unauthenticated/unenforced before Phase 1 (see below) |
| `web/app/(auth)/`, `web/app/(marketing)/landing`, `web/app/(workspace)/{admin,billing,dashboard,team}`, `web/context/AuthContext.tsx`, `web/components/{UserMenu,WorkspaceSwitcher}.tsx`, `web/lib/auth.ts` | SaaS frontend pages | Real UI; did not send auth tokens before Phase 1 |

### Honest state of the original layer, pre-Phase-1

This SaaS layer was a **skeleton, not load-bearing**, as of the start of this
work:

- 20 of 25 API routers had no `get_current_user` dependency.
- The WebSocket (`unified_ws.py`) was unauthenticated; any client could
  subscribe to any `turn_id`.
- `max_messages_per_day` and other plan limits were seeded and returned by
  the API but never checked.
- The Stripe webhook only logged events; it never updated subscription
  state. (Closed after Phase 1 — see below.)
- `ChatSession` / `ChatMessage` rows were never written — `/admin/stats` and
  `/analytics/learner` queried permanently empty tables.
- `passlib`/`bcrypt` were not declared as dependencies, so a clean install
  silently fell back to unsalted-round SHA-256 password hashing.
- A quiz-ID IDOR allowed fetching another user's quiz by guessing its id.

### Phase 1 status

Closed:

- All 20 previously-unauthenticated routers now require `get_current_user`
  (pure-HTTP routers at the router level; routers mixing HTTP with legacy
  per-feature WebSocket endpoints via a `_secure` sub-router, since
  `get_current_user`'s `HTTPBearer` dependency can't resolve against a
  `WebSocket`).
- `unified_ws.py`'s `/ws` now requires `get_ws_user`, and
  `subscribe_turn`/`subscribe_session`/`cancel_turn`/`resume_from` check
  session ownership against the connected user (via the new Postgres
  mirror) rather than accepting any `turn_id`/`session_id` a client sends.
- `ChatSession`/`ChatMessage` are now written, via a non-fatal mirror hook
  in `TurnRuntimeManager._persist_and_publish`
  (`meridian/persistence/mirror.py`) — the same tap point powering the WS
  ownership check and `max_messages_per_day` enforcement.
  `/admin/stats`/`/analytics/learner` already queried these tables
  correctly; they were just always empty. No route code changed — they
  now return real numbers because the underlying tables are finally
  populated.
- `passlib`/`bcrypt` are declared dependencies (`bcrypt<4.1` pinned — newer
  bcrypt removed an attribute passlib 1.7.4 probes); the module now raises
  at import time instead of silently falling back to SHA-256.
- The quiz-ID IDOR is fixed (`get_quiz`, `submit_quiz`, `add_flashcard` in
  `meridian/api/learning.py` now filter by the caller's `user_id`).
- `CORS_ORIGINS` replaces `allow_origins=["*"]` + `allow_credentials=True`.
- `max_messages_per_day` is now enforced (`meridian/platform/quota.py`),
  wired into the WS chat path since chat has no HTTP request to attach a
  FastAPI dependency to.
- `response.usage` is captured end-to-end (`deeptutor/services/llm/usage.py`,
  a contextvars-based per-turn scope — not a process-global dict, unlike
  `BaseAgent._shared_stats`) and lands on the mirrored `ChatMessage` rows'
  `prompt_tokens`/`completion_tokens`, which were permanently NULL before.
- The `words × 1.3` estimator (`llm_stats.estimate_tokens`) is replaced with
  tiktoken's `cl100k_base` BPE encoding — it's now only a fallback for calls
  with no real usage number, not the default.
- Alembic has a real initial migration
  (`meridian/persistence/migrations/versions/`), verified to render and
  apply against Postgres via `alembic upgrade head --sql`.
- The Stripe webhook (`meridian/api/billing.py`) now fulfills events instead
  of only logging them: `checkout.session.completed` creates or activates a
  `Subscription` from the checkout session's metadata (`user_id`,
  `plan_id`); `customer.subscription.updated`/`.deleted` sync `status`
  (mapped from Stripe's status vocabulary), `current_period_start/end`,
  `trial_end`, and `canceled_at`; `invoice.paid` upserts an `Invoice` row,
  keyed on `stripe_invoice_id` so a Stripe redelivery updates the existing
  row instead of creating a duplicate (Stripe redelivers on a timeout even
  after a successful `200`, so this idempotency is load-bearing, not
  defensive-for-its-own-sake). Fulfillment handlers take plain dicts rather
  than the `stripe` SDK's typed objects, so they're unit-testable without
  the (optional) `stripe` package installed; a fulfillment bug is caught,
  logged, and still returns `{"received": True}` — the non-fatal hook
  pattern used everywhere else in this fork — because failing the webhook
  response makes Stripe retry an event that will keep failing the same way.
  15 tests in `tests/api/test_stripe_webhook.py`, run against a real
  in-memory DB.

Still open (tracked here, not silently skipped):

- `BaseAgent._shared_stats` (the process-global, module-keyed dict) still
  exists for the CLI's own pretty-printed run summary; it was not deleted,
  only bypassed for the path that matters for SaaS billing/observability
  (real usage now flows through `deeptutor/services/llm/usage.py` instead).
- `require_tenant` (`meridian/platform/auth/dependencies.py`) exists but has
  no consumer yet — every current endpoint is already correctly
  user-scoped or role-gated; it's the documented, ready-to-use dependency
  for the first genuinely org-scoped endpoint.
- Redis, durable queues, SMTP, and org invite acceptance remain deferred,
  as originally scoped for Phase 1.

## New original work beyond `d3abe6b`

Everything under `meridian/learner/`, `meridian/knowledge/`,
`meridian/curriculum/`, `meridian/evaluation/`, `meridian/observability/`,
and `meridian/bridge/` is new original work added after the initial SaaS
scaffolding, per the phased plan in `ARCHITECTURE.md`. These did not exist
in DeepTutor. As of this writing: 62 files, ~7,200 lines under `meridian/`,
with 97 tests specifically for the new Phase 2-6 modules (part of a
309-passing/15-known-failing full suite, up from a 188-passing/27-failing
baseline — see "Baseline test triage" below for what those 15 are; the
Stripe webhook fulfillment work below Phase 1 accounts for the other 15
new tests beyond that 97).
Verify with `git ls-files meridian/ | xargs wc -l` and `pytest -q`.

| Module | What it is | Tests |
|---|---|---|
| `meridian/learner/mastery.py` | Beta-Bernoulli mastery kernel: `mastery = α/(α+β)`, `confidence` from posterior variance, time-decay toward the prior, difficulty-weighted updates | 12 property tests |
| `meridian/learner/service.py` | ORM adapter for the kernel (`record_event`, `get_mastery_map`) | 5 tests against a real in-memory DB |
| `meridian/learner/misconceptions.py` | Signature-matching against known error patterns per concept | 7 tests |
| `meridian/knowledge/graph.py` | Prerequisite DAG: transitive closure, cycle rejection, topological order | 8 tests |
| `meridian/knowledge/diagnosis.py` | Walks the DAG upstream from a target concept and names the weakest link — the headline demo behavior | 6 tests, including a full scripted-event-log replay through the real kernel |
| `meridian/knowledge/seed_calculus.py` | The hand-authored one-domain DAG (11 concepts, arithmetic → gradient_descent) prototyping concept tagging before general extraction | — (seed data) |
| `meridian/curriculum/planner.py` | Priority-weighted topological scheduler over the DAG, respecting a time budget | 7 tests |
| `meridian/curriculum/autopilot.py` | Composes the above into the full diagnose→plan→teach→assess→replan loop | 3 tests running the whole loop end to end |
| `meridian/evaluation/model_metadata.py` | Consolidates the three previously-divergent `MODEL_PRICING` tables into one catalog with pricing, context window, and capability metadata | 5 tests |
| `meridian/evaluation/harness.py` | Scores a model against a set of cases via an injected `model_fn` — testable offline, no live API needed | 6 tests with a fake model |
| `meridian/evaluation/router.py` | Picks a model from the catalog given hard constraints (context window, capabilities) and a cost/quality-weighted policy | 6 tests |
| `meridian/observability/spans.py` | Contextvars-propagated span model (duration, parent-child, status) — what `core/trace.py` isn't | 8 tests, including a concurrency-isolation test |
| `meridian/observability/export.py` | Structured-log sink always; OpenTelemetry export if installed (optional dependency) | 2 tests |
| `meridian/observability/event_log.py` | The subscriber that finally drains `deeptutor.events.EventBus` | 4 tests |
| `meridian/platform/quota.py` | Enforces `Plan.max_messages_per_day`, which was seeded and returned but never checked | 5 tests against a real in-memory DB |
| `meridian/persistence/mirror.py` | Non-fatal Postgres mirror of the engine's SQLite turn/session store | exercised via the quota/service tests above |

No performance, latency, or cost numbers are claimed anywhere above beyond
"N tests pass" — that's the one class of claim this repository's own test
suite reproduces on demand. Anything requiring a live LLM call (a real
`meridian/evaluation/harness.py` benchmark run, an actual routing table
built from measured quality scores) has not been run in this sandboxed
build environment and is not claimed as done.

### Baseline test triage

The pre-existing 15 failures (of 324 collected, non-skipped tests) left
after `pytest -q` are unrelated to this fork's own changes — verified by
reproducing each in isolation before touching anything nearby:
research request-config mapping, the provider-CLI docs contract, litellm
factory mocking assumptions that predate this work, a RAG pipeline
integration test needing embedding config this environment doesn't have,
and one test-order-dependent `model_catalog` pair. Two *were* fixed as
part of Phase 0 (`test_config_loader`, `test_prompt_parity` — both were
silently-broken checks, not merely failing ones; see that commit for
detail), and the stale `src` → `deeptutor` import bug that caused the
bulk of the original 27 failures is fixed.

## License

Both the inherited engine and this fork's original additions are licensed
under the Apache License, Version 2.0 (see `LICENSE`). This document and
`NOTICE` satisfy the attribution requirements of §4 of that license; they do
not alter its terms.
