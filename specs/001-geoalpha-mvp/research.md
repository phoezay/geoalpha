# Phase 0 Research: GeoAlpha MVP

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-11-02

All findings below were verified against upstream source code (shallow clones read on
2026-11-02), not just READMEs. Upstream revisions: TradingAgents `v0.7.1` (c454491),
Kronos `67b630e` (2026-04-13), WorldMonitor `main` @ 2026-11-02 (Python SDK 0.1.2).

---

## R1. How to add a Geopolitical Analyst to TradingAgents without forking

**Finding**: TradingAgents has no analyst plugin API. `ANALYST_NODE_SPECS` in
`tradingagents/graph/analyst_execution.py` is a fixed registry, and the Bull/Bear researchers
build their prompts from four hard-coded report keys (`market_report`, `sentiment_report`,
`news_report`, `fundamentals_report`). A fifth analyst registered at runtime would run, but
no downstream agent would read its report.

However, `instrument_context` (built by `TradingAgentsGraph.resolve_instrument_context`
inside `create_run_state`) appears in the prompts of **every** agent: all four analysts, Bull/Bear
researchers, Research Manager, Trader, all three risk debaters, and the Portfolio Manager.

**Decision**: Run the Geopolitical Analyst and the Kronos forecast as **GeoAlpha-owned stages
before** the TradingAgents graph. Subclass `TradingAgentsGraph` as `GeoAlphaTradingGraph` and
override `create_run_state` so that `instrument_context` = upstream identity text + a compact,
clearly delimited **"GeoAlpha Evidence"** block (top geopolitical signals with IDs, and the
forecast summary). Every agent then reasons over the evidence.

**Rationale**: Composition by subclass rather than a fork (Constitution VI). It reaches every
agent with one override. The upstream version is pinned and a contract test asserts the
override point still exists and that the evidence block reaches the Bull, Bear and Portfolio
Manager prompts.

**Alternatives considered**:
- *Fork TradingAgents and add a 5th analyst*: most faithful to "an extra analyst", but it
  violates Principle VI and creates a merge burden on a fast-moving upstream (7 releases in
  4 months).
- *Append to `news_report` after the analysts finish*: only reaches the researchers, not the
  Trader or risk team, and it mutates an upstream report, which breaks attribution.
- *Inject via `portfolio_context`*: does not reach analysts or researchers.

**Risk**: Upstream renames `create_run_state` or `instrument_context`. Mitigated by
pinning the version and adding a contract test (T-contract `test_tradingagents_override_points`).

---

## R2. Per-stage progress from TradingAgents

**Finding**: `TradingAgentsGraph.stream_run()` wraps `graph.stream(..., subgraphs=True,
stream_mode=["values","tasks"])` but drops the namespace, so the node name is lost. LangGraph
`tasks` events carry the node `name` (e.g. "Market Analyst", "Bull Researcher", "Trader",
"Portfolio Manager") and fire at start and at finish.

**Decision**: `GeoAlphaTradingGraph.run_with_events()` calls `self.graph.stream(...)` directly
with `stream_mode=["tasks","values"]` and `subgraphs=True`, inside the same
`run_config_context(self.config)` that upstream uses. It maps node names to GeoAlpha stage
keys with a static table (see data-model.md, *Stage keys*), emitting `stage.started` and
`stage.completed` events. The final state is taken from the last top-level `values` chunk,
and `record_decision()` is then called as upstream does.

**Alternatives**: LangChain callback handlers (`callbacks=` ctor arg). They give LLM-level events
but not clean node boundaries, so they were rejected for stage tracking. They may still be used
later for token and cost accounting.

---

## R3. Retry semantics (FR-005)

**Finding**: TradingAgents supports LangGraph SQLite checkpoints (`checkpoint_enabled`,
default False). With them on, re-invoking the same ticker, date and graph shape resumes from
the last completed node.

**Decision**:
- GeoAlpha stages (`geo`, `forecast`) have their own timeouts (geo 120 s, forecast 180 s).
  They retry automatically once with backoff. If they still fail, the run **continues** with
  the input recorded as missing (FR-004).
- TradingAgents stages run with `checkpoint_enabled=True`. A failed or timed-out TA stage marks
  the run `failed`, and **Retry** resumes from the checkpoint, so only the failed stage and
  the ones after it re-run.
- On a *completed* run whose geo or forecast input is missing, the UI offers **"Re-run with
  fresh inputs"**, which creates a new linked run (`retry_of`). A completed decision is never
  silently rewritten (spec edge case: no silent overwrite).

---

## R4. Geopolitical data source (WorldMonitor)

**Findings**:
- The official Python SDK `worldmonitor-sdk` 0.1.2 is **MIT-licensed**, stdlib-only, Python
  ≥ 3.9. The AGPL-3.0 platform is only *called*, never vendored.
- The SDK has curated helpers: `world_brief`, `country_risk(cc)`, `country_brief(cc)`,
  `conflict_events(country=…)`, `sanctions_data(country=…)`, `maritime_activity(cc)`,
  `news_intelligence(country=…, topic=…)`, `natural_disasters`, `cyber_threats`,
  `forecast_predictions(region=…)`, plus `call_tool(name, **args)`. All accept a server-side
  `jmespath=` projection, which cuts payloads by 80–95%.
- **Hosted API**: every data tool except `get_sources` needs a **paid Pro API key**
  (`WORLDMONITOR_API_KEY`).
- **Self-hosted** (Docker Compose): free. The MCP server is at `/api/mcp` and
  authenticated with an operator key we generate (`WORLDMONITOR_VALID_KEYS`). Most feeds work
  with no key or free signups (ACLED, FRED, EIA, etc.). The SDK supports this through
  `base_url` and `mcp_url`.
- The data is **live only**. There is no historical query.

**Decision**: Define a `GeoProvider` protocol with three implementations, chosen by
`GEOALPHA_GEO_PROVIDER`:
1. `worldmonitor`: the SDK client, configured for hosted (Pro key) or self-hosted (`base_url`,
   `mcp_url` and an operator key) entirely through environment variables.
2. `snapshot`: reads only from GeoAlpha's own snapshot store (used for past dates, and offline).
3. `fixture`: deterministic JSON fixtures for tests, demos, and running without any key.

**Point-in-time rule (Constitution I, FR-009)**:
- Live calls are allowed **only** when `analysis_date` is the *current* session: today (ET)
  or the latest completed session. Before 16:00 ET the default date is yesterday's session, so
  an "only today" rule would make geo unavailable for nearly every normal run. Every live
  response is persisted as a `GeoSnapshot` (`captured_at = now`, `as_of = analysis_date`).
  *Refined 2026-11-03 during implementation.* Because `captured_at` is recorded honestly, a
  snapshot taken the morning after D is never eligible for a later backtest of D, so
  historical evaluation stays leak-free.
- For any earlier date, only snapshots with `captured_at ≤ analysis_date 23:59:59 ET` and
  `captured_at ≥ analysis_date − 3 days` are eligible. If none exist, the stage outcome is
  `unavailable` (not `failed`), and the UI shows "Geopolitical data unavailable for this date".
- `geoalpha snapshot` (CLI) captures a daily snapshot for a watchlist so history builds up.
  It can be scheduled with Windows Task Scheduler or cron. This is the foundation for the next
  feature (backtesting).

**Alternatives**: calling the MCP endpoint over raw HTTP (rejected because the SDK already does
it with zero dependencies). GDELT and ACLED directly (rejected for the MVP because they duplicate
WorldMonitor's aggregation, but they remain a fallback if WorldMonitor access is not possible).

**Open operator choice** (not a spec ambiguity, it only affects the environment): hosted Pro key
vs. self-hosted Docker. Both are supported with no code difference. Quickstart covers `fixture`
mode so the MVP is demonstrable with neither.

---

## R5. Mapping a ticker to its geopolitical exposure

**Decision**: There are two LLM steps inside the `geo` stage, both using TradingAgents' own
LLM client factory (`create_tier_client(config, "quick")`) with structured output, so one
provider configuration serves everything:
1. **Exposure profile**: input is the company profile from yfinance as of `analysis_date`
   (name, sector, industry, country, business summary). The output is
   `ExposureProfile{countries[ISO2, weight, reason], commodities[], chokepoints[], themes[]}`,
   capped at 6 countries. It is cached per (ticker, quarter).
2. **Signal assessment**: input is the exposure profile plus WorldMonitor results fetched for
   those countries (`country_risk`, `conflict_events(limit=10)`, `sanctions_data`,
   `maritime_activity` where chokepoints apply), and `world_brief` projected with jmespath. The
   output is a ranked list of up to 10 `GeoSignal`s, each with category, severity 1–5, impact
   direction and rationale, plus an overall `geo_materiality` (`material` | `immaterial`). Every
   signal must reference a `source_ref` taken from the fetched payloads. Signals without a
   source are dropped by a validator, which enforces Principle II.

---

## R6. Kronos forecasting

**Findings**:
- Kronos is not packaged (no `pyproject.toml` or `setup.py`). The code is `model/kronos.py`
  and `model/module.py` (MIT). Weights are on Hugging Face: `NeoQuasar/Kronos-small` (24.7M
  params, context 512) and `NeoQuasar/Kronos-Tokenizer-base`.
- Its `requirements.txt` pins `pandas==2.2.2`, which **conflicts** with TradingAgents'
  `pandas>=3.0.6`. The model code only uses basic pandas and NumPy operations.
- `auto_regressive_inference` **averages** across `sample_count` internally
  (`np.mean(preds, axis=1)`), so a single call cannot produce an uncertainty band.
- `KronosPredictor.predict_batch(df_list, …)` runs several series in parallel.

**Decision**:
- **Vendor** `model/` at commit `67b630e` into `backend/src/geoalpha/vendor/kronos/`, keeping
  `LICENSE` and recording it in `THIRD_PARTY_LICENSES.md`. Our dependency set (pandas 3, torch
  ≥ 2.3 CPU) applies, and a smoke test runs one tiny forecast. This is recorded in Complexity
  Tracking.
- **Uncertainty band**: call `predict_batch` with **N = 30 copies** of the same history
  (`sample_count=1`, `T=1.0`, `top_p=0.9`). That gives 30 independent sample paths, from which
  we take per-step p10, p50 and p90 of `close`. Summary: expected move = p50 at the horizon vs.
  last close (in %), and range = [p10, p90] at the horizon.
- Data: daily OHLCV from yfinance, filtered to `date ≤ analysis_date`, lookback 400 bars,
  `pred_len = 5`. Future timestamps come from NYSE sessions via `exchange_calendars` (XNYS).
  If fewer than 120 bars are available, the stage outcome is `unavailable` (spec US3-AS3).
- Model: `Kronos-small` on CPU by default (CUDA if present). The model is loaded once per
  worker process and kept warm.

**Alternatives**: run Kronos in a separate process with its own pandas 2.2 environment
(rejected because it adds a second runtime). Use the `max_context` 2048 `Kronos-mini` (rejected
because it is less accurate, though it could be a config option).

---

## R7. Confidence and evidence citation (FR-014, SC-004)

**Finding**: TradingAgents' `PortfolioDecision` schema has a 5-tier `rating`
(Buy/Overweight/Hold/Underweight/Sell) and a rationale, but **no confidence field**.

**Decision**: Add a final GeoAlpha **`decision_card`** step (quick-tier LLM, structured
output) that takes the PM decision, the geo signals and the forecast summary, and returns
`DecisionCard{confidence: low|medium|high, summary, cited_signal_ids[], forecast_alignment:
supports|contradicts|neutral|unavailable, geo_statement: cites|none_material|unavailable}`.
A validator enforces that either `cited_signal_ids` is non-empty **or** `geo_statement` is
`none_material` or `unavailable`, which makes SC-004 testable. Confidence is capped at
`medium` when any input is missing.

---

## R8. Backend runtime, persistence and streaming

**Decisions**:
- **Python 3.12** managed with `uv`. FastAPI and Uvicorn. Pydantic v2 for every contract.
- **Persistence**: SQLite through SQLAlchemy 2.0 (typed ORM), with a single file under
  `GEOALPHA_DATA_DIR`. LangGraph checkpoints use their own SQLite file.
- **Background execution**: an in-process `RunWorker` with a bounded `ThreadPoolExecutor`
  (default 2 concurrent runs). Runs are owned by the server, not by the HTTP request, so
  closing the browser does not affect them (FR-006). On startup, runs left `running` are
  marked `interrupted` and become resumable through checkpoints.
- **Live progress**: Server-Sent Events at `GET /api/runs/{id}/events`. Events are also
  persisted (`run_events` table), so reconnecting clients replay from `Last-Event-ID`.
  `GET /api/runs/{id}` returns the full snapshot for reloads and history (SC-007).
- **Alternatives**: WebSockets (unnecessary since traffic is one-way). Celery or Redis
  (rejected under YAGNI for a single-user local tool).

---

## R9. Frontend stack, skeletons and charts

**Decisions**:
- **React 19, Vite 6, TypeScript (strict), Tailwind CSS v4** (`@tailwindcss/vite`), with
  `@theme` tokens for colour, radius and spacing. Dark mode follows the system and has a manual
  toggle (`class` strategy).
- **Server state**: TanStack Query v5. SSE events patch the query cache
  (`queryClient.setQueryData`), so each panel derives loading, empty, error or loaded from
  one source.
- **`<AsyncRegion>` primitive**: every async panel renders through
  `AsyncRegion{status, skeleton, empty, error, children}`. It enforces Principle IV in one
  place: a skeleton that has the same box size as the content (fixed `min-h`/aspect ratio per
  panel), a timeout that leads to the error state, and a retry callback.
- **Skeleton primitive**: `<Skeleton>` uses `animate-pulse` with `motion-reduce:animate-none`,
  `bg-neutral-200 dark:bg-neutral-800`, and `aria-hidden`. The region carries
  `aria-busy="true"` and an `sr-only` "Loading …" label.
- **Charts**: TradingView `lightweight-charts` v5 (Apache-2.0) draws candlesticks for history,
  a p50 line, and a p10–p90 band (two area series, a technique documented upstream). The chart
  container has a fixed aspect ratio, so the skeleton and chart sizes match (no CLS).
- **Markdown** (agent reports): `react-markdown` + `remark-gfm`, styled with
  `@tailwindcss/typography`.
- **Routing**: React Router v7, with routes `/` (new analysis), `/runs/:id`, and `/history`.
- **Alternatives**: Recharts (rejected because it has no native candlesticks), Next.js
  (rejected because there is no SSR or SEO need, so the plain Vite single-page app is simpler).

---

## R10. Testing strategy

**Decisions**:
- **Backend**: pytest. Providers are mocked at the protocol boundary (`FakeGeoProvider`,
  `FakePriceSource`, and a fake LLM via langchain-core `FakeListChatModel`), so the suite runs
  offline (Principle V).
  - **Look-ahead tests** (SC-005): for each source, put rows or snapshots dated after
    `analysis_date` into the fakes and assert they never reach stage inputs.
  - **Contract tests**: the OpenAPI schema is generated from the app and compared with
    `contracts/openapi.yaml`, and SSE event payloads are validated against
    `contracts/sse-events.schema.json`.
  - **Upstream override tests**: the TradingAgents override points exist, and the evidence block
    appears in the Bull, Bear and PM prompts.
  - `@pytest.mark.integration` covers real Kronos and network calls and is excluded by default.
- **Frontend**: Vitest + Testing Library + MSW. Every async component is tested in its
  loading, empty, error and loaded states. Playwright e2e runs the full fixture-mode flow,
  measures CLS through `PerformanceObserver('layout-shift')` (SC-003 < 0.1), and checks
  reduced-motion with `page.emulateMedia({reducedMotion:'reduce'})`.
- Accessibility: `@axe-core/playwright` on each route in light and dark mode.
