# Implementation Plan: GeoAlpha MVP: Geopolitically-Aware Ticker Analysis

**Branch**: `001-geoalpha-mvp` | **Date**: 2026-11-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-geoalpha-mvp/spec.md`

## Summary

A local web app where a researcher enters a US ticker and date and gets a TradingAgents
decision that has reasoned over (a) geopolitical signals from WorldMonitor relevant to the
company's exposure and (b) a Kronos 5-session price forecast with an uncertainty band. The
report streams in stage by stage over SSE into a clean Tailwind dashboard, where every
region shows a skeleton with the same layout until its stage completes.

Technical approach (from [research.md](./research.md)):
- The **geo** and **forecast** stages are GeoAlpha-owned and run in parallel *before*
  TradingAgents. Their results go into every TradingAgents agent through a
  `GeoAlphaTradingGraph` subclass that adds a "GeoAlpha Evidence" block to
  `instrument_context` (R1). There is no fork.
- Stage progress comes from LangGraph `tasks` events mapped to 10 stage keys (R2).
  Checkpoints let failed runs resume (R3).
- Point-in-time rule: live WorldMonitor calls happen only for today's session and are
  snapshotted. Past dates use snapshots only, otherwise `unavailable` (R4).
- Kronos is vendored (MIT) because of a pandas pin conflict. The band comes from 30 batched
  sample paths, p10/p50/p90 (R6).
- A final structured `decision_card` step adds confidence and enforced geo citations (R7).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x strict (frontend)

**Primary Dependencies**: Backend: FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0,
`tradingagents==0.7.1` (git tag), `worldmonitor-sdk==0.1.2`, torch ≥ 2.3 (CPU), huggingface_hub,
einops, safetensors, yfinance, exchange_calendars, sse-starlette. Frontend: React 19, Vite 6,
Tailwind CSS v4 (+ typography plugin), TanStack Query v5, React Router v7,
lightweight-charts v5, react-markdown + remark-gfm.

**Storage**: SQLite (app DB) + SQLite (LangGraph checkpoints) under `GEOALPHA_DATA_DIR`. HF model cache on local disk.

**Testing**: pytest (+ jsonschema for contracts), ruff, mypy; Vitest + Testing Library + MSW; Playwright + @axe-core/playwright

**Target Platform**: Local workstation (Windows Server 2025 here; also macOS/Linux), modern evergreen browsers

**Project Type**: Web application (Python API + worker in one process; React SPA)

**Performance Goals**: Skeleton visible in under 1 s after submit (SC-001). Full run finishes in 10 min or less at p90 (SC-002). Kronos forecast (30 paths, CPU) in 60 s or less. Past run opens in under 2 s (SC-007).

**Constraints**: No look-ahead (Principle I). CLS < 0.1 (Principle IV). Offline-capable test suite. No live trading. WorldMonitor is consumed only through its MIT SDK (AGPL boundary).

**Scale/Scope**: 1 user / small trusted team, ≤ 2 concurrent runs, ~3 routes, ~10 async regions, 10 stages per run.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (below).*

| # | Principle | How the design complies | Status |
|---|---|---|---|
| I | Point-in-Time Integrity | GeoSnapshot eligibility rule (live calls only for today's session, else snapshots with `captured_at ≤ D`), price bars filtered to `date ≤ analysis_date`, `as_of` and `captured_at` on every snapshot, and a look-ahead regression test per source (SC-005) | ✅ Pass |
| II | Explainable, Attributed Signals | Signals require `snapshot_id` and a source. Decision card validator: cites signals or explicitly states none_material/unavailable. Debate and analyst reports are exposed. Model, provider, date and disclaimer are on every report. Sample band shown | ✅ Pass |
| III | Clean Tailwind UI/UX | Tailwind v4 tokens, one accent (indigo), shared `components/ui` primitives, light/dark, 360px, keyboard and axe checks (see [ui-states.md](./contracts/ui-states.md)) | ✅ Pass |
| IV | Skeleton-First Loading | `<AsyncRegion>` enforces skeleton/empty/error/ready with fixed min-heights, a timeout to error, and reduced-motion. Spinners only inside `Button`. Stage-by-stage SSE reveal. CLS checked in e2e | ✅ Pass |
| V | Test-Backed Changes | Fakes at the provider boundaries, contract tests for OpenAPI/SSE, upstream override-point tests, four-state component tests, offline by default | ✅ Pass |
| VI | Simplicity & Composition | TradingAgents is used as a pinned dependency and extended by subclass. WorldMonitor through its SDK. One process and one SPA. **Exception: Kronos vendored** (see Complexity Tracking) | ⚠️ Justified |
| — | Tech & licensing constraints | Python/FastAPI/Pydantic and React/Vite/Tailwind as mandated. `THIRD_PARTY_LICENSES.md` (TradingAgents Apache-2.0, Kronos MIT, worldmonitor-sdk MIT, lightweight-charts Apache-2.0). Secrets only through env. No order placement | ✅ Pass |

**Post-design re-check (after Phase 1)**: The data model, contracts and UI contract were reviewed against all
six principles. No new violations. The `unavailable` stage status (distinct from `failed`) and
the `geo_statement` enum were added specifically to satisfy I and II. **Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/001-geoalpha-mvp/
├── plan.md              # This file
├── research.md          # Phase 0: verified upstream findings & decisions (R1–R10)
├── data-model.md        # Phase 1: entities, state machines, validation rules
├── quickstart.md        # Phase 1: setup + 13 validation scenarios
├── contracts/
│   ├── openapi.yaml           # REST API
│   ├── sse-events.schema.json # live progress events
│   └── ui-states.md           # views, async regions, skeleton/empty/error contract, tokens
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks; not created here)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml                 # uv-managed; tradingagents pinned to git tag v0.7.1
├── src/geoalpha/
│   ├── api/                       # FastAPI app, routes (runs, health, tickers), SSE endpoint, problem+json
│   ├── core/                      # settings (env), market calendar & date rules, logging
│   ├── db/                        # SQLAlchemy models + repositories (runs, stages, events, snapshots, …)
│   ├── geo/
│   │   ├── provider.py            # GeoProvider protocol + eligibility rule
│   │   ├── worldmonitor.py        # SDK adapter (hosted or self-hosted)
│   │   ├── fixture.py             # deterministic fixtures (XOM, KO, LMT, TSM, NEWIPO …)
│   │   ├── exposure.py            # ExposureProfile LLM step (cached)
│   │   └── analyst.py             # signal assessment → GeoSignals + materiality
│   ├── forecast/
│   │   ├── prices.py              # PriceSource protocol, yfinance + fixture impls, PIT filter
│   │   └── kronos_service.py      # warm model, batched sampling → p10/p50/p90
│   ├── agents/
│   │   ├── graph.py               # GeoAlphaTradingGraph (instrument_context override, run_with_events)
│   │   ├── evidence.py            # renders the "GeoAlpha Evidence" block
│   │   ├── stage_map.py           # LangGraph node name → StageKey
│   │   └── decision_card.py       # structured confidence + citations + validator
│   ├── runner/
│   │   ├── orchestrator.py        # stage pipeline, timeouts, retries, missing_inputs
│   │   ├── worker.py              # bounded thread pool, startup recovery
│   │   └── events.py              # RunEvent persistence + pub/sub for SSE
│   ├── vendor/kronos/             # vendored upstream model/ @67b630e + LICENSE
│   └── cli.py                     # `geoalpha serve`, `geoalpha snapshot`
└── tests/
    ├── unit/                      # transforms, eligibility rule, stage map, validators
    ├── contract/                  # OpenAPI diff, SSE schema, TradingAgents override points
    ├── lookahead/                 # one regression test per data source (SC-005)
    └── integration/               # @pytest.mark.integration: real Kronos / network

frontend/
├── package.json  vite.config.ts  tsconfig.json
├── src/
│   ├── styles/app.css             # @import "tailwindcss"; @theme tokens; reduced-motion base
│   ├── components/ui/             # Card, Button, Badge, Stat, Table, Tabs, Drawer, Skeleton, AsyncRegion, …
│   ├── lib/                       # api client (typed from openapi), query client, SSE → cache bridge
│   ├── features/
│   │   ├── new-run/               # form, ticker validation, config banner, recent runs
│   │   ├── run-report/            # header, stage rail, decision card, geo panel, forecast chart, reports, debate
│   │   └── history/               # runs table / mobile cards
│   └── routes/                    # router setup: /, /runs/:id, /history
└── tests/
    ├── unit/                      # Vitest four-state tests per async component
    └── e2e/                       # Playwright: flow, CLS, a11y, reduced motion, 360px

THIRD_PARTY_LICENSES.md
.env.example
```

**Structure Decision**: Web application with `backend/` (Python package `geoalpha`, API and
background worker in one process) and `frontend/` (Vite SPA). In development, the Vite dev
server proxies `/api` to the backend. One process per side keeps Principle VI. A separate
worker service is deferred until it is needed.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Vendoring Kronos `model/` (2 files, MIT) into `backend/src/geoalpha/vendor/kronos/` | Kronos has no package metadata, so it can't be installed as a dependency. Its `pandas==2.2.2` pin conflicts with TradingAgents' `pandas>=3.0.6` | (a) git dependency: impossible without `pyproject.toml`. (b) a separate Python env/process for Kronos: a second runtime, IPC and deployment surface for ~600 lines of model code. Mitigation: pin the commit in a `VENDORED.md`, keep the upstream LICENSE, make no local edits (wrapper only), and add a smoke test |
| Subclassing `TradingAgentsGraph` (overriding `create_run_state`, custom stream loop) | Upstream has no analyst plugin API. This is the only non-fork way to reach every agent's prompt and get per-node progress | Forking (merge burden on a fast-moving upstream) or patching `news_report` (reaches too few agents, breaks attribution). Mitigation: exact version pin and contract tests on the override points |

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| WorldMonitor hosted data needs a paid Pro key | Fixture mode for the demo and tests. Self-hosted Docker supported through env vars, with no code change |
| Point-in-time geo history starts empty | Explicit `unavailable` state. `geoalpha snapshot` scheduled daily to build history (needed by the next backtesting feature) |
| LLM cost/latency per run (≈ 12–20 LLM calls) | Quick tier for geo and decision card, 1 debate round default, concurrency cap of 2, model and provider shown on every report |
| Upstream TradingAgents changes break the override | Pinned tag. Contract tests fail loudly on upgrade |
| Kronos CPU time | Kronos-small, 30 samples batched, model kept warm. Runs in parallel with the geo stage |
