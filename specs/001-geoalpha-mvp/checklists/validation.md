# Validation Record: GeoAlpha MVP (T097)

**Date**: 2026-11-03 · **Branch**: `001-geoalpha-mvp` · **Machine**: Windows Server 2025, CPU only
**Mode**: offline demo (`GEOALPHA_ENGINE=fake`, `GEOALPHA_GEO_PROVIDER=fixture`). Kronos was real in
manual runs and synthetic in e2e (`GEOALPHA_FAKE_FORECAST=1`).

## Automated checks

| Check | Result |
|---|---|
| `uv run pytest` (unit, contract, look-ahead) | ✅ 73 passed |
| `uv run pytest -m integration` (real Kronos-small, CPU) | ✅ 1 passed |
| `uv run ruff check` / `ruff format --check` / `mypy` (strict, 48 files) | ✅ clean |
| `npm run typecheck` / `npm run lint` | ✅ clean (3 react-refresh warnings, no errors) |
| `npm test` (Vitest four-state component tests) | ✅ 23 passed |
| `npm run e2e` (Playwright: flow, CLS, axe light+dark, 360px, reduced motion, keyboard) | ✅ 11 passed |

## Quickstart scenarios

| # | Scenario | Result | Evidence |
|---|---|---|---|
| 1 | Happy path | ✅ | e2e `XOM`: skeleton in 219–816 ms (SC-001 < 1 s), CLS ≈ 0.000004 (SC-003 < 0.1), 10/10 stages, rating + confidence + cited chips + disclaimer + model |
| 2 | Geo explainability | ✅ | GeoPanel test; e2e: clicking a chip focuses `#signal-…`; rows show region, category, severity, impact label, valid time, source link |
| 3 | No material exposure | ✅ | e2e `KO`: empty state + "No material geopolitical factors" (`geo_statement=none_material`) |
| 4 | Past date, no snapshot | ✅ (unit) | `test_geo_lookahead.py`: past date → `unavailable`, **0 live calls**; snapshots after D or older than D−3 are never eligible. Not run against live WorldMonitor (no key) |
| 5 | Forecast | ✅ | Real Kronos-small run in the browser: 30 sample paths, ~6 s on CPU, band + p50 + stats; history ends at the analysis date (`test_price_lookahead.py`) |
| 6 | Too little history | ✅ | e2e `NEWIPO`: "Not enough price history", run completes, "Missing inputs: price forecast", confidence ≤ medium |
| 7 | Geo source down | ⚠️ partial | Failure path covered: a failing pre-stage → `failed` after 1 retry → run continues (`orchestrator`); WorldMonitor auth errors map to "WorldMonitor rejected the API key." Not exercised against the live service (no key) |
| 8 | Reload mid-run | ✅ | e2e reload test; server owns runs; SSE replays from `Last-Event-ID` (`test_replay_after_last_event_id`) |
| 9 | Validation | ✅ | e2e + `test_run_create_validation.py` (bad pattern, unknown ticker, future date → 422) |
| 10 | Weekend date | ✅ | `test_weekend_rolls_back_to_friday`; header shows "adjusted from …" |
| 11 | Missing LLM key | ✅ | `test_config_problem_blocks_run`: 503 + `/api/health.problems`; ConfigBanner renders them |
| 12 | History | ✅ | `test_list_runs.py`, HistoryTable test; completed runs load from the snapshot without a stream |
| 13 | UI quality | ✅ | e2e: axe clean in light and dark, 360px no horizontal scroll, reduced motion → `animation-name: none`, visible focus ring |

## Not yet validated (needs credentials)

- **Real TradingAgents run** (`GEOALPHA_ENGINE=tradingagents`): no LLM key on this machine. The
  integration is covered by contract tests against the installed upstream code (override points,
  node names, and the evidence block reaching the Bull, Bear, Trader and Portfolio Manager prompts),
  but SC-002 (≤ 10 min p90) and the live stage-event mapping still need one real run.
- **Live WorldMonitor** (hosted Pro key or self-hosted stack).

## Issues found and fixed during validation

| Issue | Fix |
|---|---|
| 360px page widened to 1310px by sr-only spans escaping the chip scroller | `relative` on the scroller |
| Report grid columns grew to their content on mobile | `grid-cols-1` (`minmax(0,1fr)`) |
| First POST ~1 s because of the cold NYSE calendar | Warm it up at startup (skeleton now 219 ms) |
| Event `seq` race when geo and forecast publish concurrently | Serialised publish |
| SQLite "database is locked" on read→write upgrade under concurrency | `BEGIN IMMEDIATE` + no nested sessions |
| WCAG contrast in neutral badges (light) and tinted bubbles (dark); chart `role=img` wrapped a link | Token adjustments; chart is now a `<figure>` |
