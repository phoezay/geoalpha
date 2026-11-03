---
description: "Task list for GeoAlpha MVP"
---

# Tasks: GeoAlpha MVP: Geopolitically-Aware Ticker Analysis

**Input**: Design documents from `specs/001-geoalpha-mvp/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: INCLUDED. Constitution Principle V requires look-ahead tests per data source,
contract tests, and four-state (loading/empty/error/loaded) tests for every async UI component.

**Organization**: Tasks are grouped by user story. **Delivery order follows a user instruction
and differs from the spec's priority numbers.** The commonly built core lands first (the
TradingAgents web dashboard, then the Kronos chart), then the geopolitical layer, history and export:

| Phase | Story | Spec priority | What it delivers |
|---|---|---|---|
| 3 | US1 | P1 | Run → live stage progress → decision card + report tabs (TradingAgents dashboard) |
| 4 | US3 | P3 | Kronos forecast stage + chart with p10–p90 band |
| 5 | US2 | P2 | Geopolitical Analyst stage + geo panel + evidence injection + citations |
| 6 | US4 | P4 | Run history |
| 7 | US5 | P5 | Export to Markdown / HTML |

Until their phases land, the `geo` and `forecast` stages are created with status `skipped`.
In that case the decision card reports `geo_statement = "unavailable"` and
`forecast_alignment = "unavailable"`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story the task belongs to (US1–US5)
- Paths: `backend/src/geoalpha/…`, `backend/tests/…`, `frontend/src/…`, `frontend/tests/…`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and tooling

- [X] T001 Create the directory skeleton from plan.md (backend/src/geoalpha/{api,core,db,geo,forecast,agents,runner,vendor}, backend/tests/{unit,contract,lookahead,integration}, frontend/src/{styles,components/ui,lib,features,routes}, frontend/tests/{unit,e2e}), each Python package with an `__init__.py`
- [X] T002 Create backend/pyproject.toml (uv, `requires-python = ">=3.12"`) with dependencies: fastapi, uvicorn[standard], pydantic>=2, pydantic-settings, sqlalchemy>=2, sse-starlette, `tradingagents @ git+https://github.com/TauricResearch/TradingAgents@v0.7.1`, worldmonitor-sdk==0.1.2, torch>=2.3 (CPU index for Windows/Linux), huggingface_hub, einops, safetensors, yfinance, exchange_calendars, python-ulid, typer, markdown-it-py; dev: pytest, pytest-asyncio, httpx, jsonschema, pyyaml, ruff, mypy; `[project.scripts] geoalpha = "geoalpha.cli:app"`; pytest markers `integration` (excluded by default via `addopts = "-m 'not integration'"`). Then run `uv sync`
- [X] T003 [P] Scaffold frontend with Vite React-TS in frontend/ and install react@19, react-dom@19, react-router@7, @tanstack/react-query@5, lightweight-charts@5, react-markdown, remark-gfm, tailwindcss@4, @tailwindcss/vite, @tailwindcss/typography, clsx; dev: vitest, @testing-library/react, @testing-library/user-event, @testing-library/jest-dom, jsdom, msw, @playwright/test, @axe-core/playwright, openapi-typescript, eslint, typescript-eslint. Add scripts `dev`, `build`, `typecheck`, `lint`, `test`, `e2e`, `gen:api`
- [X] T004 [P] Configure backend lint and types in backend/pyproject.toml (`[tool.ruff]` line-length 100, select E,F,I,B,UP; `[tool.mypy]` strict for `geoalpha.*`, ignore_missing_imports for tradingagents, worldmonitor_sdk and vendor)
- [X] T005 [P] Configure frontend/vite.config.ts (plugins: react, @tailwindcss/vite; dev server proxy `/api` → `http://127.0.0.1:8000`; vitest env jsdom + setup file frontend/tests/setup.ts with jest-dom and an MSW server) and set `"strict": true, "noUncheckedIndexedAccess": true` in frontend/tsconfig.json
- [X] T006 [P] Create .env.example at repo root with every variable from quickstart.md (`GEOALPHA_GEO_PROVIDER=fixture`, `GEOALPHA_DATA_DIR=./data`, `GEOALPHA_ENGINE=tradingagents`, `TRADINGAGENTS_LLM_PROVIDER=anthropic`, `TRADINGAGENTS_DEEP_THINK_LLM=claude-opus-5-5`, `TRADINGAGENTS_QUICK_THINK_LLM=claude-sonnet-5`, `ANTHROPIC_API_KEY=`, `WORLDMONITOR_API_KEY=`, `WORLDMONITOR_BASE_URL=`, `WORLDMONITOR_MCP_URL=`, `GEOALPHA_FORECAST_MODEL=NeoQuasar/Kronos-small`, `GEOALPHA_MAX_CONCURRENT_RUNS=2`), and add `data/` to .gitignore
- [X] T007 [P] Create THIRD_PARTY_LICENSES.md at repo root listing TradingAgents (Apache-2.0, v0.7.1), Kronos (MIT, commit 67b630e, vendored), worldmonitor-sdk (MIT 0.1.2; the WorldMonitor platform is AGPL-3.0 and is only called over the network, never vendored), and lightweight-charts (Apache-2.0)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, persistence, run orchestration skeleton, SSE, API shell, UI primitives.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Backend core

- [X] T008 Implement settings in backend/src/geoalpha/core/settings.py with pydantic-settings, reading every `.env.example` variable. `engine: Literal["tradingagents","fake"]` (`fake` = scripted offline engine for e2e and demo), `geo_provider: Literal["worldmonitor","snapshot","fixture"]`, `data_dir` (created on startup), and a `problems()` method that returns user-facing config problems (e.g. "ANTHROPIC_API_KEY is not set" when engine=tradingagents and provider=anthropic)
- [X] T009 [P] Implement the market calendar in backend/src/geoalpha/core/market_calendar.py with exchange_calendars XNYS: `today_et()`, `last_completed_session(now)`, `roll_back_to_session(d) -> date` (weekend or holiday → previous session), `next_sessions(d, n) -> list[date]`, `is_future(d)` (compared with today in America/New_York)
- [X] T010 [P] Implement structured logging in backend/src/geoalpha/core/logging.py (JSON lines with a `run_id` contextvar; technical errors are logged here, never sent to clients)
- [X] T011 Implement SQLAlchemy 2.0 models in backend/src/geoalpha/db/models.py per data-model.md. `AnalysisRun` (id ULID PK; ticker; requested_date; analysis_date; status enum `queued|running|completed|failed|interrupted`; created_at/started_at/finished_at; llm_provider, deep_model, quick_model; settings JSON; retry_of FK nullable; missing_inputs JSON list of `geo|forecast`; error). `Stage` (composite PK run_id+key; key enum `geo|forecast|market|sentiment|news|fundamentals|research_debate|trader|risk_debate|decision`; order; critical bool, false only for geo/forecast; status enum `pending|running|done|failed|unavailable|skipped`; started_at/finished_at; timeout_s with geo 120, forecast 180, TA stages 600; report_md; payload JSON; error; attempts). `RunEvent` (run_id, seq per-run monotonic, type, data JSON, at). `Decision` (run_id PK; rating enum `Buy|Overweight|Hold|Underweight|Sell`; confidence enum `low|medium|high`; summary ≤600 chars; rationale_md; geo_statement enum `cites|none_material|unavailable`; cited_signal_ids JSON; forecast_alignment enum `supports|contradicts|neutral|unavailable`; missing_inputs JSON)
- [X] T012 Implement the engine/session factory and `init_db()` in backend/src/geoalpha/db/session.py (SQLite file `{data_dir}/geoalpha.db`, WAL mode, `check_same_thread=False`)
- [X] T013 Implement repositories in backend/src/geoalpha/db/repo.py: `create_run_with_stages(run)` creates all 10 Stage rows up front (SC-001), `get_run_detail(id)`, `update_stage(...)`, `append_event(run_id, type, data) -> seq`, `events_after(run_id, seq)`, `save_decision(...)`, `mark_running_as_interrupted()`, `list_runs(limit, cursor)` newest first by ULID
- [X] T014 Implement Pydantic API schemas in backend/src/geoalpha/api/schemas.py that mirror contracts/openapi.yaml exactly (Health, TickerValidation, RunCreate, Stage, GeoSignal, GeoSummary, Bar, ForecastPoint, PriceForecast, Decision, RunSummary, RunPage, RunDetail, Problem), with field constraints copied verbatim (e.g. GeoSignal `severity` 1–5, `headline` maxLength 140, `rank` 1–10)
- [X] T015 Implement the event bus in backend/src/geoalpha/runner/events.py: `publish(run_id, type, data)` persists through `repo.append_event`, then notifies in-process subscribers (thread-safe `asyncio.Queue` per subscriber via `loop.call_soon_threadsafe`). `subscribe(run_id, after_seq)` replays from the DB, then streams live
- [X] T016 Implement the stage pipeline skeleton in backend/src/geoalpha/runner/orchestrator.py. `run_analysis(run_id)` sets the run to running and emits `run.started`. It runs **pre-stages** (`geo`, `forecast`) concurrently through a pluggable registry `PRE_STAGES: dict[StageKey, Callable]`; unregistered pre-stages are set to `skipped`. Each pre-stage gets its `timeout_s`, one automatic retry with 2 s backoff, and is non-critical: failure → `failed` + adds to `missing_inputs`; `unavailable` outcome → `unavailable` + adds to `missing_inputs` (FR-004). It then calls the engine (T018/T024) with an `on_stage(key, status, report_md, payload)` callback and finally emits `run.finished`. Stage transitions emit `stage.started|completed|failed|unavailable` events per contracts/sse-events.schema.json
- [X] T017 Implement the worker in backend/src/geoalpha/runner/worker.py: a `ThreadPoolExecutor(max_workers=settings.max_concurrent_runs)`, `submit(run_id)`, and startup recovery that calls `repo.mark_running_as_interrupted()` (FR-006)
- [X] T018 [P] Implement the offline scripted engine in backend/src/geoalpha/runner/fake_engine.py (`engine=fake`). It walks the 8 TradingAgents stage keys in order with 0.5–1.5 s delays, emits canned markdown reports from backend/src/geoalpha/runner/fixtures/fake_reports/{ticker or default}.md, and returns a PM decision text + rating. It honours ticker `FAILME` by failing `trader` (used by e2e retry tests)
- [X] T019 Implement the FastAPI app factory in backend/src/geoalpha/api/app.py: lifespan (init_db, worker start, recovery), RFC 9457 problem+json exception handlers (422 field_errors, 404, 409, 503), and routers. Implement `GET /api/health` in backend/src/geoalpha/api/routes_health.py, returning `Health` with `problems` from settings
- [X] T020 Implement the SSE endpoint `GET /api/runs/{runId}/events` in backend/src/geoalpha/api/routes_events.py with sse-starlette: `id`=seq, `event`=type, `data`=JSON. Honour the `Last-Event-ID` header, send a `heartbeat` every 15 s, and close after `run.finished`
- [X] T021 Implement `geoalpha serve` (uvicorn on 127.0.0.1:8000) in backend/src/geoalpha/cli.py with typer

### Foundational tests

- [X] T022 [P] Contract test in backend/tests/contract/test_openapi_contract.py: load specs/001-geoalpha-mvp/contracts/openapi.yaml and `app.openapi()`, and assert that every path, method, operationId and component schema name in the contract exists with the same required fields and enum values
- [X] T023 [P] Contract test in backend/tests/contract/test_sse_events.py: run one `engine=fake` run end to end with TestClient, collect the SSE messages, and validate each `data` against contracts/sse-events.schema.json (resolve `openapi.yaml#/components/...` refs with a jsonschema referencing Registry)

### Frontend foundation

- [X] T024 Create design tokens and base styles in frontend/src/styles/app.css: `@import "tailwindcss"; @plugin "@tailwindcss/typography";`, the `@theme` tokens from contracts/ui-states.md (bg, surface, border, muted, accent=indigo, positive=emerald, negative=rose, warning=amber, skeleton) with dark overrides via `@custom-variant dark (&:where(.dark, .dark *))`, Inter font, and `body` with explicit background and text colour
- [X] T025 [P] Implement UI primitives in frontend/src/components/ui/: Card.tsx, Button.tsx (primary/secondary/ghost; `loading` prop shows the inline spinner, the **only** spinner allowed in the app), Badge.tsx, Stat.tsx, Tabs.tsx (roving tabindex, arrow keys), Table.tsx, EmptyState.tsx, ErrorState.tsx (message + Retry button), Disclaimer.tsx ("Research output, not financial advice."), ThemeToggle.tsx (system default + manual `.dark` class, persisted in try/catch-guarded localStorage); all with `focus-visible:ring-2 ring-accent ring-offset-2`
- [X] T026 Implement frontend/src/components/ui/Skeleton.tsx (`Skeleton` block and `SkeletonText lines`): `animate-pulse motion-reduce:animate-none bg-skeleton rounded-md`, `aria-hidden="true"`
- [X] T027 Implement frontend/src/components/ui/AsyncRegion.tsx per contracts/ui-states.md: props `status: 'loading'|'empty'|'error'|'ready'`, `skeleton`, `empty`, `error`, `onRetry`, `timeoutMs`, `minHeightClass`, `label`. The container always keeps `minHeightClass`; loading sets `aria-busy="true"` plus an sr-only "Loading {label}…"; loading longer than timeoutMs switches to ErrorState "Taking longer than expected"
- [X] T028 [P] Four-state test in frontend/tests/unit/AsyncRegion.test.tsx: renders the skeleton (aria-busy) while loading, the empty node, ErrorState whose Retry calls onRetry, and children when ready; with fake timers, loading turns into error after timeoutMs; there are no `role="progressbar"` elements
- [X] T029 Generate API types with `npm run gen:api` (openapi-typescript ../specs/001-geoalpha-mvp/contracts/openapi.yaml -o src/lib/api-types.ts) and implement the typed fetch client in frontend/src/lib/api.ts (parses problem+json into an `ApiError` with `fieldErrors`)
- [X] T030 Implement the query client and the SSE→cache bridge in frontend/src/lib/runStream.ts: `useRunStream(runId)` opens an `EventSource('/api/runs/{id}/events')` and applies each event to the `['run', id]` RunDetail cache via `queryClient.setQueryData` (stage status, report_md, payload, geo/forecast/decision objects, run status). It closes on `run.finished`; on reconnect the browser's automatic `Last-Event-ID` handles replay
- [X] T031 Implement the app shell and routes in frontend/src/routes/router.tsx and frontend/src/main.tsx: a top bar (logo "GeoAlpha", nav: New analysis / History, ThemeToggle), routes `/`, `/runs/:id`, `/history`, and a `max-w-7xl px-4 sm:px-6` container

**Checkpoint**: The app boots, `/api/health` works, fake runs stream events, and the primitives are tested.

---

## Phase 3: User Story 1 - Run an analysis and get a decision (Spec P1) 🎯 MVP

**Goal**: The commonly built TradingAgents web dashboard. Enter a ticker and date, watch the 10-stage
rail and the report skeleton fill stage by stage, then get a decision card (rating, confidence,
summary) and report tabs (analysts, debate, trader/risk).

**Independent Test**: With `GEOALPHA_ENGINE=fake`, start a run for XOM. The skeleton appears in under 1 s,
sections fill independently, and the decision card shows rating, confidence, summary, model/date and the
disclaimer. With `engine=tradingagents` and a real key, the same flow yields a real decision.

### Tests for User Story 1 ⚠️ (write first, ensure they fail)

- [X] T032 [P] [US1] Contract test in backend/tests/contract/test_tradingagents_override_points.py: assert that `TradingAgentsGraph` has `create_run_state`, `resolve_instrument_context`, `record_decision`, `graph`, `config`, and that `tradingagents.dataflows.config` (or wherever v0.7.1 defines it) exposes `run_config_context`; assert that `tradingagents.__version__ == "0.7.1"`
- [X] T033 [P] [US1] Unit test in backend/tests/unit/test_stage_map.py: every upstream node name (`Market Analyst`, `Sentiment Analyst`, `News Analyst`, `Fundamentals Analyst`, `Bull Researcher`, `Bear Researcher`, `Research Manager`, `Trader`, `Aggressive Analyst`, `Conservative Analyst`, `Neutral Analyst`, `Portfolio Manager`) maps to the stage key in data-model.md; a multi-node stage completes only after its last node
- [X] T034 [P] [US1] Unit test in backend/tests/unit/test_run_create_validation.py: ticker regex `^[A-Za-z][A-Za-z0-9.\-]{0,9}$` is upper-cased; a future date → 422 with `field_errors.date`; a Saturday → `analysis_date` = Friday and `requested_date` = Saturday; no date → last completed session
- [X] T035 [P] [US1] Unit test in backend/tests/unit/test_decision_card.py: the validator rejects `geo_statement="cites"` with an empty `cited_signal_ids` and a non-empty list with any other statement; confidence is capped at `medium` when `missing_inputs` is non-empty; when geo is skipped → `geo_statement="unavailable"`
- [X] T036 [P] [US1] Integration test in backend/tests/unit/test_run_flow_fake.py: POST /api/runs (engine=fake) → 201 with 10 stages `pending` (geo/forecast `skipped` once the run starts) → poll GET until completed → decision present, `llm_provider`/`deep_model` populated; ticker `FAILME` → run `failed`, then POST retry `mode=resume` → completes
- [X] T037 [P] [US1] Four-state tests in frontend/tests/unit/RunReport.test.tsx with MSW + a mocked EventSource: an initial RunDetail with all stages pending renders the decision/report skeletons; a `stage.completed` for `market` swaps only the Market tab content; a `stage.failed` shows ErrorState with Retry; a completed run renders the rating Stat with its text label and the Disclaimer

### Backend implementation for User Story 1

- [X] T038 [P] [US1] Implement the ticker resolver in backend/src/geoalpha/core/tickers.py: `validate(ticker) -> TickerValidation` using yfinance `Ticker(t).fast_info`/`info` (quoteType EQUITY or ETF, US exchange); results cached for 24 h in memory; when engine=fake, accepts tickers present in runner/fixtures plus `FAILME`
- [X] T039 [P] [US1] Implement the node→stage map in backend/src/geoalpha/agents/stage_map.py (table from data-model.md *Stage keys*), with a `StageTracker` that turns node start/finish task events into stage-level `running`/`done` transitions
- [X] T040 [US1] Implement `GeoAlphaTradingGraph(TradingAgentsGraph)` in backend/src/geoalpha/agents/graph.py. Constructor builds the config from settings (llm_provider, deep/quick models, `max_debate_rounds=1`, `checkpoint_enabled=True`, `results_dir={data_dir}/ta`); `evidence_block: str` attribute (empty for now); override `create_run_state` to append `evidence_block` to `instrument_context`; `run_with_events(ticker, date, on_node)` iterates `self.graph.stream(graph_input, subgraphs=True, stream_mode=["tasks","values"])` inside `run_config_context(self.config)` per research R2, calls `on_node(name, "start"|"finish", result)`, keeps the last top-level values as final_state, then calls `record_decision` and `clear_checkpoint_on_success` as upstream `_run_graph` does
- [X] T041 [US1] Implement the TradingAgents engine adapter in backend/src/geoalpha/runner/ta_engine.py: runs `GeoAlphaTradingGraph.run_with_events` and uses StageTracker to call the orchestrator's `on_stage`. Stage `report_md` comes from state keys: market_report, sentiment_report, news_report, fundamentals_report, `investment_debate_state` (payload `{bull_history, bear_history, judge}` + investment_plan markdown), trader_investment_plan, `risk_debate_state` (payload of the three histories), final_trade_decision. Enforces per-stage `timeout_s` (600) by watchdog → raises a StageTimeout that marks the stage `failed`
- [X] T042 [US1] Implement the decision card in backend/src/geoalpha/agents/decision_card.py: `build_decision_card(pm_text, rating, geo_summary|None, forecast|None, missing_inputs) -> Decision` with the quick-tier client from `tradingagents.llm_clients.factory.create_tier_client(config, "quick")` and structured output (Pydantic `DecisionCard`), plus the validator from T035; the fake engine uses a deterministic builder
- [X] T043 [US1] Wire the `decision` stage end in backend/src/geoalpha/runner/orchestrator.py: after Portfolio Manager finishes, build and save the Decision, emit `decision.ready`, then mark the stage `done`
- [X] T044 [US1] Implement run routes in backend/src/geoalpha/api/routes_runs.py: `POST /api/runs` (validate → 503 if `settings.problems()` → create run + stages → worker.submit → 201 RunDetail), `GET /api/runs/{id}` (RunDetail incl. `last_event_seq`), `POST /api/runs/{id}/retry` (`resume`: failed/interrupted → reset failed and later stages to pending, resubmit with the same checkpoint thread; `fresh`: new run with `retry_of`; completed + resume → 409). Implement `GET /api/tickers/validate` in backend/src/geoalpha/api/routes_tickers.py

### Frontend implementation for User Story 1

- [X] T045 [P] [US1] Implement the new-run form in frontend/src/features/new-run/NewRunForm.tsx: ticker input (auto-uppercase, debounced 300 ms validation through `/api/tickers/validate`, inline error, muted "Checking…" text, no spinner); date input (default last session, `max` = today); primary Analyze button disabled until valid; on submit POST, then `navigate('/runs/' + id)` immediately and seed the query cache with the 201 response (SC-001)
- [X] T046 [P] [US1] Implement the config banner in frontend/src/features/new-run/ConfigBanner.tsx: AsyncRegion over `/api/health` (h-10 skeleton); renders an amber banner listing `problems`, hidden when there are none
- [X] T047 [US1] Compose the page in frontend/src/routes/NewRunPage.tsx (hero title "Analyze a ticker", one-line description, ConfigBanner, NewRunForm in a Card)
- [X] T048 [P] [US1] Implement the run header in frontend/src/features/run-report/RunHeader.tsx: ticker, analysis date + "adjusted from {requested_date}" note when they differ, status Badge, model/provider meta, Disclaimer; fixed h-20 with a skeleton
- [X] T049 [P] [US1] Implement the stage rail in frontend/src/features/run-report/StageRail.tsx: 10 chips in order (pending outline, running accent pulse with `motion-reduce:animate-none`, done check, failed rose with Retry, unavailable amber, skipped muted); horizontal on lg, the chip row scrolls horizontally on mobile (`overflow-x-auto`) without page overflow; `aria-live="polite"` announcement on status change
- [X] T050 [P] [US1] Implement the decision card in frontend/src/features/run-report/DecisionCard.tsx: AsyncRegion `min-h-48`; the rating as a large Stat coloured by token (Buy/Overweight positive, Hold neutral, Underweight/Sell negative) **with its text label**; confidence Badge; summary; forecast-alignment line; amber "Missing inputs: …" note; a cited-signal chips slot (filled by US2); skeleton = big stat block + 3 text lines + 2 badges
- [X] T051 [P] [US1] Implement analyst report tabs in frontend/src/features/run-report/AnalystTabs.tsx: Tabs Market / Sentiment / News / Fundamentals; each panel is an AsyncRegion (`min-h-64`, skeleton = 6 text lines) rendering `report_md` with react-markdown + remark-gfm inside `prose dark:prose-invert max-w-none`; a skipped stage → EmptyState "This analyst was not part of the run"
- [X] T052 [P] [US1] Implement the debate panel in frontend/src/features/run-report/DebatePanel.tsx: alternating Bull and Bear turns (from payload) + Research Manager verdict; skeleton = 3 alternating bubbles; `min-h-64`
- [X] T053 [P] [US1] Implement the trader and risk panel in frontend/src/features/run-report/TraderRiskPanel.tsx: trader plan markdown + 3 risk perspectives (collapsible); skeleton = 4 text blocks; `min-h-64`
- [X] T054 [US1] Compose the run report page in frontend/src/routes/RunReportPage.tsx: `useQuery(['run', id])` + `useRunStream(id)`; layout per ui-states.md (header, rail, a 12-col grid with DecisionCard col-span-12, **geo and forecast placeholder slots** col-span-7/5 with fixed min heights (skeleton while pending, EmptyState "Not part of this run" when the stage is skipped), then AnalystTabs, then DebatePanel + TraderRiskPanel side by side); each region's status is derived from its stage status; Retry calls POST retry `resume`

**Checkpoint**: US1 is fully functional with the fake engine and with the real TradingAgents engine. This matches the typical TradingAgents web GUI, with progressive skeleton loading added.

---

## Phase 4: User Story 3 - Model price forecast (Spec P3)

**Goal**: The Kronos forecast stage runs before TradingAgents. The chart shows candles up to the
analysis date plus the p50 line and p10–p90 band, and the forecast summary goes into the agents' context.

**Independent Test**: Run XOM; the Forecast panel shows history ending at the analysis date, a 5-session path
with a band, and stats (last close, expected move %, range). Run NEWIPO (fixture) → "Not enough price history".

### Tests for User Story 3 ⚠️

- [X] T055 [P] [US3] Look-ahead test in backend/tests/lookahead/test_price_lookahead.py: a FakePriceSource with bars after `analysis_date` → `PriceSource.history(ticker, analysis_date)` never returns a bar with `date > analysis_date`, and the model input frame's last row date == analysis_date
- [X] T056 [P] [US3] Unit test in backend/tests/unit/test_forecast_quantiles.py: given 30 synthetic sample paths, p10 ≤ p50 ≤ p90 at every step, `path` length == horizon, `expected_move_pct == (p50[h]/last_close − 1)×100`, `range_low/high == p10[h]/p90[h]`; fewer than 120 bars → outcome `unavailable`
- [X] T057 [P] [US3] Four-state test in frontend/tests/unit/ForecastPanel.test.tsx: skeleton keeps `aspect-[16/10]`; unavailable → EmptyState "Not enough price history to forecast"; error → Retry; ready → the stats render (chart lib mocked)
- [X] T058 [P] [US3] Integration smoke test (marked `@pytest.mark.integration`) in backend/tests/integration/test_kronos_smoke.py: load Kronos-small and run 4 samples × 5 steps on 200 synthetic bars; the output shape is correct and contains no NaNs

### Implementation for User Story 3

- [X] T059 [US3] Vendor Kronos: copy upstream `model/__init__.py`, `model/kronos.py`, `model/module.py` at commit 67b630e into backend/src/geoalpha/vendor/kronos/ unmodified, add its LICENSE, and add backend/src/geoalpha/vendor/kronos/VENDORED.md (source URL, commit, date, "no local edits; wrap only")
- [X] T060 [P] [US3] Implement price sources in backend/src/geoalpha/forecast/prices.py: `PriceSource` protocol `history(ticker, analysis_date, lookback) -> DataFrame[date, open, high, low, close, volume]` filtered to `date ≤ analysis_date` (Principle I); `YFinancePriceSource` (auto_adjust=False, 2-year window ending on analysis_date+1 then filtered); `FixturePriceSource` reading backend/src/geoalpha/forecast/fixtures/{ticker}.csv (XOM, KO, LMT, TSM, GLD with 400 bars; NEWIPO with 60 bars)
- [X] T061 [US3] Implement backend/src/geoalpha/forecast/kronos_service.py: a lazily loaded singleton `KronosPredictor(Kronos.from_pretrained(settings.forecast_model), KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base"), max_context=512)` on CUDA if available else CPU; `forecast(bars, analysis_date, horizon=5, samples=30) -> PriceForecast` calls `predict_batch` with 30 copies (`sample_count=1, T=1.0, top_p=0.9, verbose=False`), y-timestamps from `market_calendar.next_sessions`, per-step p10/p50/p90 of close, a summary per data-model.md, `history` = last 120 bars; < 120 bars → raises `Unavailable("Not enough price history to forecast")`
- [X] T062 [US3] Add the `PriceForecast` table (run_id PK; model; history JSON; lookback_bars; horizon; path JSON validated with `p10 ≤ p50 ≤ p90` and length = horizon; sample_count; last_close; expected_move_pct; range_low; range_high) to backend/src/geoalpha/db/models.py and to repo save/get, and include `forecast` in RunDetail
- [X] T063 [US3] Register the `forecast` pre-stage in backend/src/geoalpha/runner/orchestrator.py (`PRE_STAGES["forecast"]`): run kronos_service in the worker thread with timeout 180 s, save PriceForecast, emit `forecast.ready`; the fake engine uses FixturePriceSource + Kronos (or a deterministic synthetic band when `GEOALPHA_FAKE_FORECAST=1` for fast e2e)
- [X] T064 [US3] Implement the evidence renderer in backend/src/geoalpha/agents/evidence.py, forecast section: a delimited `### GeoAlpha Evidence` block with "Price model (Kronos-small, 30 samples, as of {date}): expected {±x.x%} over 5 sessions, p10–p90 range {lo}–{hi}. Treat as one probabilistic input." Wire `GeoAlphaTradingGraph.evidence_block` from the orchestrator before the TA engine starts; decision card `forecast_alignment` now computed
- [X] T065 [P] [US3] Implement frontend/src/features/run-report/ForecastPanel.tsx: AsyncRegion (`aspect-[16/10]` chart box + `h-16` stats row); lightweight-charts v5 chart with CandlestickSeries (history), LineSeries p50 (accent, dashed), a p10–p90 band (an AreaSeries at p90 filled with accent at 15% opacity + an AreaSeries at p10 filled with the surface colour), a vertical marker at the analysis date; theme-aware colours read from CSS variables and re-applied on theme change; ResizeObserver to fit; Stat row: Last close · Expected move (±%, coloured with a text sign) · Range p10–p90
- [X] T066 [US3] Replace the forecast placeholder slot in frontend/src/routes/RunReportPage.tsx with ForecastPanel (lg:col-span-5)

**Checkpoint**: Dashboard + forecast chart. This matches what people commonly build from TradingAgents and Kronos.

---

## Phase 5: User Story 2 - Geopolitical exposure behind the decision (Spec P2)

**Goal**: The Geopolitical Analyst pre-stage (WorldMonitor or fixture), point-in-time snapshots,
ranked sourced signals, evidence injected into every agent, and cited signals on the decision card.

**Independent Test**: In fixture mode, run XOM → a ranked geo panel with region/category/severity/impact/
valid time/source link, and decision chips that scroll to the cited rows. Run KO → the "No material exposure"
empty state. A past date with provider `snapshot` and no snapshots → "unavailable for this date".

### Tests for User Story 2 ⚠️

- [X] T067 [P] [US2] Look-ahead test in backend/tests/lookahead/test_geo_lookahead.py: snapshots captured after `analysis_date 23:59:59 ET` or before `analysis_date − 3d` are never eligible; a past date with no eligible snapshot → outcome `unavailable` and **zero live provider calls** (assert the spy call count is 0); D == today → a live call happens and a snapshot is persisted with `captured_at` and `as_of`
- [X] T068 [P] [US2] Unit test in backend/tests/unit/test_geo_signals.py: signals without a `snapshot_id`/`source_label` are dropped; at most 10 signals, ranked 1..n; `severity` is clamped to 1–5; the materiality is `immaterial` when no signals remain
- [X] T069 [P] [US2] Prompt-injection test in backend/tests/contract/test_evidence_reaches_agents.py: with a fake LLM (langchain-core `FakeListChatModel`) capturing prompts, run GeoAlphaTradingGraph with a sentinel evidence block, and assert that the sentinel appears in the Bull Researcher, Bear Researcher, Trader and Portfolio Manager prompts
- [X] T070 [P] [US2] Four-state test in frontend/tests/unit/GeoPanel.test.tsx: skeleton of 5 rows; immaterial → "No material geopolitical exposure detected for {date}"; unavailable → amber note with the reason; error → Retry; ready → rows show severity dots, category badge, impact with a **text label**, and a source link with `rel="noopener noreferrer"`; expanding a row shows the rationale

### Implementation for User Story 2

- [X] T071 [US2] Add tables to backend/src/geoalpha/db/models.py + repo: `GeoSnapshot` (id; tool; params_hash SHA-256 of canonical JSON; params; payload; as_of date; captured_at immutable; source_mode `hosted|self_hosted|fixture`; index `(tool, params_hash, captured_at DESC)`), `ExposureProfile` (PK ticker+quarter `YYYYQn`; countries list of `{iso2, weight 0–1, reason}` with 1–6 entries and weights summing to ≤1; commodities; chokepoints; themes ≤5), `RunGeoSignal` (id `run_id:n`; rank 1–10; region; category enum `conflict|instability|sanctions|supply_route|commodity_shock|energy|cyber|disaster|policy|other`; severity 1–5; impact_direction `positive|negative|mixed|uncertain`; headline ≤140 chars; rationale; valid_at; snapshot_id **required**; source_label; source_url nullable)
- [X] T072 [US2] Implement backend/src/geoalpha/geo/provider.py: a `GeoProvider` protocol (`world_brief`, `country_risk(cc)`, `conflict_events(cc, limit)`, `sanctions(cc)`, `maritime(cc)`, each → payload dict) and `SnapshottingProvider(inner, repo, analysis_date)` that applies the eligibility rule from data-model.md (live calls + persist when D == `today_et()`; else the latest snapshot with `D−3d ≤ captured_at ≤ D 23:59:59 ET`; else raise `Unavailable("Geopolitical data unavailable for this date")`)
- [X] T073 [P] [US2] Implement backend/src/geoalpha/geo/worldmonitor.py: an adapter over `worldmonitor_sdk.Client(api_key, base_url, mcp_url, timeout=30)` from settings, using `jmespath` projections to trim payloads; maps `MCPError`/`APIError` to a user-facing `GeoSourceError` (auth failure → "WorldMonitor key rejected"); `source_mode` = `self_hosted` when base_url is set, else `hosted`
- [X] T074 [P] [US2] Implement backend/src/geoalpha/geo/fixture.py + backend/src/geoalpha/geo/fixtures/*.json: deterministic payloads for world_brief and for countries US, SA, IR, IL, YE, TW, CN, RU, UA, with source labels/URLs; exposure fixtures for XOM (US, SA, Hormuz, Red Sea), LMT (US, UA, TW), TSM (TW, CN, Taiwan Strait), GLD (global), KO (US, low exposure → immaterial)
- [X] T075 [US2] Implement backend/src/geoalpha/geo/exposure.py: `get_exposure(ticker, analysis_date)` cached per (ticker, quarter); the company profile from yfinance `info` (longName, sector, industry, country, longBusinessSummary) → quick-tier structured output `ExposureProfile` (≤6 countries, commodities, chokepoints, themes); fixture mode reads the exposure fixtures
- [X] T076 [US2] Implement backend/src/geoalpha/geo/analyst.py: `run_geo_stage(run, provider)` gets the exposure, then for each country fetches risk, conflict events (limit 10) and sanctions, maritime when chokepoints exist, plus the world brief; quick-tier structured output → ranked `GeoSignal`s referencing snapshot ids, validated per T068; returns GeoSummary + a `report_md` narrative; fixture mode uses a deterministic assessor (no LLM) so e2e is offline
- [X] T077 [US2] Register the `geo` pre-stage in backend/src/geoalpha/runner/orchestrator.py (timeout 120 s, 1 retry; `Unavailable` → stage `unavailable`), persist RunGeoSignals, emit `geo.ready`, and include `geo` in RunDetail
- [X] T078 [US2] Extend backend/src/geoalpha/agents/evidence.py with a geopolitical section: top ≤6 signals as `[{id}] {region} · {category} · sev {n} · {impact}: {headline} (source: {label}, valid {date})`, the materiality line, or "Geopolitical data unavailable for this date; do not assume absence of risk."; instruct agents to cite signal ids
- [X] T079 [US2] Extend backend/src/geoalpha/agents/decision_card.py so cited_signal_ids must be ids from this run's signals; `geo_statement` is derived (signals cited → `cites`; materiality immaterial → `none_material`; geo unavailable/failed/skipped → `unavailable`) (SC-004)
- [X] T080 [US2] Implement `geoalpha snapshot --watchlist XOM,CVX,...` in backend/src/geoalpha/cli.py: for each ticker, resolve the exposure and capture today's snapshots through SnapshottingProvider (no LLM assessment), printing a count per tool
- [X] T081 [P] [US2] Implement frontend/src/features/run-report/GeoPanel.tsx: AsyncRegion `min-h-96`; ranked rows (severity dots 1–5 with an sr-only "severity n of 5", category Badge, region, headline, impact icon ↑↓↕? + text, relative valid time with an absolute time in `title`, source link opening in a new tab); expandable rationale (button with `aria-expanded`); an exposure summary strip (countries with weights, chokepoints); immaterial/unavailable states per ui-states.md; rows have `id="signal-{id}"`
- [X] T082 [US2] Add cited-signal chips to frontend/src/features/run-report/DecisionCard.tsx: clicking one smooth-scrolls (instant under reduced motion) to `#signal-{id}` and briefly highlights the row with an accent ring; "No material geopolitical factors" / "Geopolitical data unavailable" text for the other `geo_statement` values
- [X] T083 [US2] Replace the geo placeholder slot in frontend/src/routes/RunReportPage.tsx with GeoPanel (lg:col-span-7)

**Checkpoint**: The full GeoAlpha differentiator works. Every decision either cites sourced geo signals or says why it doesn't.

---

## Phase 6: User Story 4 - Revisit past runs (Spec P4)

**Goal**: A history list (newest first) that opens saved reports without re-running them.

**Independent Test**: Complete 2 runs, reload, open `/history`, open the older one → the full report renders in under 2 s.

- [X] T084 [P] [US4] Test in backend/tests/unit/test_list_runs.py: newest first by ULID; cursor pagination; `rating` is null for unfinished runs
- [X] T085 [P] [US4] Four-state test in frontend/tests/unit/HistoryTable.test.tsx: 8 skeleton rows with the same column widths; empty → "No runs yet" + "Start an analysis" button; error → Retry; ready → linked rows; "Load more" appends skeleton rows while fetching
- [X] T086 [US4] Implement `GET /api/runs` (limit 1–100, default 25; cursor = last ULID; returns RunPage with `next_cursor`) in backend/src/geoalpha/api/routes_runs.py
- [X] T087 [P] [US4] Implement frontend/src/features/history/HistoryTable.tsx: `useInfiniteQuery`; columns ticker, analysis date, rating Badge (with label), status, finished (relative); a table on ≥ md, stacked cards below md (no horizontal page scroll); rows link to `/runs/:id`
- [X] T088 [US4] Implement frontend/src/routes/HistoryPage.tsx, and add a "Recent runs" (last 5) AsyncRegion to frontend/src/routes/NewRunPage.tsx (5 rows × h-12 skeleton; empty "No analyses yet. Start your first above.")
- [X] T089 [US4] Make completed runs load from the DB without an SSE subscription in frontend/src/lib/runStream.ts (skip EventSource when status is terminal) so that past runs open in under 2 s (SC-007)

---

## Phase 7: User Story 5 - Export a report (Spec P5)

**Goal**: Download a completed run as Markdown or self-contained HTML (FR-025).

**Independent Test**: Export a completed run in both formats; both open offline and contain the rating, confidence,
rationale, geo signals with sources, forecast summary, all analyst reports, metadata and the disclaimer.

- [X] T090 [P] [US5] Test in backend/tests/unit/test_export.py: md and html exports contain every section listed in FR-025; the filename is `{ticker}_{analysis_date}_{run_id}.{ext}`; the HTML has no external `src`/`href` resources except source links; a non-completed run → 409
- [X] T091 [US5] Implement backend/src/geoalpha/api/export.py: `render_markdown(run_detail)` (header + metadata + disclaimer, decision, geo signals table with source links, forecast summary table, analyst reports, debate, trader/risk) and `render_html(run_detail)` (markdown-it-py → HTML wrapped in a self-contained template with inline CSS mirroring the app's light theme and an inline SVG sparkline of history + p10/p50/p90)
- [X] T092 [US5] Implement `GET /api/runs/{runId}/export?format=md|html` in backend/src/geoalpha/api/routes_runs.py with `Content-Disposition: attachment`
- [X] T093 [US5] Add an Export menu (Markdown / HTML) to frontend/src/features/run-report/RunHeader.tsx: secondary Button + a keyboard-accessible menu; disabled with a tooltip "Available when the run completes" until status is completed

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T094 [P] Playwright e2e in frontend/tests/e2e/run-flow.spec.ts (webServer starts the backend with `GEOALPHA_ENGINE=fake GEOALPHA_GEO_PROVIDER=fixture GEOALPHA_FAKE_FORECAST=1` and the Vite dev server): start XOM → the skeleton is visible within 1000 ms of clicking (SC-001); every stage completes; CLS measured via a `PerformanceObserver('layout-shift')` init script is < 0.1 (SC-003); the decision cites geo chips; clicking a chip scrolls to the row; FAILME → Retry → completes
- [X] T095 [P] Playwright e2e in frontend/tests/e2e/quality.spec.ts: axe on `/`, `/runs/:id` and `/history` in light and dark → no serious/critical violations; viewport 360×740 → `scrollWidth ≤ 360` on all routes; `emulateMedia({reducedMotion:'reduce'})` → computed `animation-name` is `none` for every `[aria-hidden][class*=animate-pulse]`; Tab order reaches all controls with a visible focus ring; no `role=progressbar` outside buttons
- [X] T096 [P] Write README.md at the repo root: what GeoAlpha is, a screenshot placeholder, quickstart (link to specs/001-geoalpha-mvp/quickstart.md), provider modes (fixture / hosted / self-hosted WorldMonitor), cost note, disclaimer, licences
- [X] T097 Run the full quickstart.md validation (all automated checks + manual scenarios 1–13) and record the results in specs/001-geoalpha-mvp/checklists/validation.md
- [X] T098 Run `uv run ruff check`, `uv run mypy src`, `npm run typecheck`, `npm run lint` and fix all findings

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → user stories
- **US1 (Phase 3)**: depends only on Foundational. **MVP.**
- **US3 (Phase 4)**: depends on Foundational. Integrates with US1's page and evidence renderer (T054, T040), so do it after US1
- **US2 (Phase 5)**: depends on Foundational. Extends evidence.py (T064) and DecisionCard (T050), so do it after US3 per the requested order. It is technically independent of US3, so it can run in parallel with US3 if staffed (merge evidence.py sections carefully)
- **US4 (Phase 6)**: depends only on Foundational + the RunDetail endpoint (T044). It can start in parallel with US3/US2
- **US5 (Phase 7)**: needs RunDetail with geo + forecast for complete exports, so it comes after US2 and US3
- **Polish (Phase 8)**: after all desired stories

### Within each story

Tests first (they must fail) → models → services → endpoints → UI → page wiring.

### Key task dependencies

T011 → T013 → T015 → T016 → T017 → T019/T020 · T024 → T026 → T027 → all panels · T029 → T030 → T054 ·
T040 → T041 → T043 · T059 → T061 → T063 → T064 · T071 → T072 → T076 → T077 → T078/T079

---

## Parallel Examples

```text
# Setup: after T001/T002
T003 frontend scaffold | T004 ruff/mypy | T005 vite config | T006 .env.example | T007 licences

# Foundational: once T011–T013 exist
T018 fake engine | T022 OpenAPI contract test | T023 SSE contract test | T025 UI primitives

# US1 tests (all [P])
T032 | T033 | T034 | T035 | T036 | T037

# US1 frontend panels (all [P], different files)
T045 NewRunForm | T046 ConfigBanner | T048 RunHeader | T049 StageRail | T050 DecisionCard | T051 AnalystTabs | T052 DebatePanel | T053 TraderRiskPanel

# US3
T055 | T056 | T057 | T058 tests, then T060 prices ‖ T059 vendoring, then T065 ForecastPanel ‖ T061–T064 backend

# US2
T067 | T068 | T069 | T070 tests, then T073 worldmonitor ‖ T074 fixtures ‖ T081 GeoPanel
```

---

## Implementation Strategy

### MVP first (US1 only)

1. Phases 1–2, then Phase 3 (US1).
2. **Stop and validate**: quickstart scenarios 1 (minus the geo/forecast parts), 8, 9, 10 and 11 with `engine=fake`, then one real run with an Anthropic key.
3. Result: a polished TradingAgents web dashboard with live, skeleton-first progress. This is what most people build from TradingAgents.

### Incremental delivery

1. + US3 → Kronos forecast chart (what people build from Kronos) → demo
2. + US2 → the geopolitical layer (the GeoAlpha differentiator) → demo in fixture mode, then with WorldMonitor
3. + US4 history → + US5 export → Polish

### Notes

- [P] = different files, no dependency on incomplete tasks
- Commit after each task or logical group; stop at any checkpoint to validate
- Never let a live/current data path leak into a past-dated run (Principle I). The T055/T067 tests guard this
