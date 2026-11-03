# Quickstart & Validation Guide: GeoAlpha MVP

This guide shows the feature works end to end. Implementation details are in `tasks.md`.
Contracts: [openapi.yaml](./contracts/openapi.yaml) · [sse-events.schema.json](./contracts/sse-events.schema.json) · [ui-states.md](./contracts/ui-states.md). Data rules: [data-model.md](./data-model.md).

## Prerequisites

- Windows, macOS or Linux, with `uv` ≥ 0.12, Node.js ≥ 22, and git
- About 2 GB of free disk (torch CPU + Kronos-small weights, downloaded on first run from Hugging Face)
- An LLM provider key. The default is Anthropic (`ANTHROPIC_API_KEY`), and any TradingAgents provider works
- Geopolitical source, one of:
  - **fixture** (no key; deterministic demo data). This is the default for validation
  - **hosted WorldMonitor** (`WORLDMONITOR_API_KEY`, Pro plan)
  - **self-hosted WorldMonitor** (Docker; see upstream `SELF_HOSTING.md`). Set `WORLDMONITOR_BASE_URL`, `WORLDMONITOR_MCP_URL` and an operator key

## Setup

```powershell
cp .env.example .env            # then fill in ANTHROPIC_API_KEY (and WorldMonitor vars if used)
cd backend;  uv sync;  cd ..
cd frontend; npm install; cd ..
```

Key environment variables (all in `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `GEOALPHA_GEO_PROVIDER` | `fixture` | `worldmonitor` \| `snapshot` \| `fixture` |
| `GEOALPHA_DATA_DIR` | `./data` | SQLite DB, checkpoints, model cache |
| `TRADINGAGENTS_LLM_PROVIDER` | `anthropic` | Passed through to TradingAgents |
| `TRADINGAGENTS_DEEP_THINK_LLM` / `_QUICK_THINK_LLM` | `claude-opus-5-5` / `claude-sonnet-5` | Model tiers |
| `GEOALPHA_FORECAST_MODEL` | `NeoQuasar/Kronos-small` | Kronos variant |
| `GEOALPHA_MAX_CONCURRENT_RUNS` | `2` | Worker pool size |

## Run

```powershell
cd backend;  uv run geoalpha serve            # http://127.0.0.1:8000
cd frontend; npm run dev                      # http://127.0.0.1:5173
```

## Automated checks (offline, no keys needed)

```powershell
cd backend;  uv run pytest                     # unit + contract + look-ahead tests
cd backend;  uv run ruff check; uv run mypy src
cd frontend; npm run typecheck; npm run lint; npm test        # Vitest four-state component tests
cd frontend; npm run e2e                       # Playwright: full flow in fixture mode + CLS + a11y + reduced motion
```

Expected: everything is green. `pytest -m integration` (real Kronos and network) is optional.

## Manual validation scenarios

| # | Scenario | Steps | Expected outcome | Covers |
|---|---|---|---|---|
| 1 | Happy path | `/` → ticker `XOM`, default date → Analyze | You land on `/runs/:id` in under 1 s, and the full skeleton plus the 10-stage rail are visible. Sections fill one at a time without jumping. The decision card shows the rating, confidence badge, summary and cited geo chips, and the disclaimer and model are in the header | US1, FR-001/3/14/16/20/21, SC-001/3/4 |
| 2 | Geo explainability | On the completed run, open the Geopolitical panel and expand a row | Each row shows region, category, severity, impact (icon + text), valid time and a source link. Clicking a cited chip in the decision scrolls to and highlights the row | US2, FR-008 |
| 3 | No material exposure | Run `KO` in fixture mode (the fixture set marks KO as having no material exposure) | The geo panel shows the "No material geopolitical exposure detected" empty state. The decision's `geo_statement = none_material` | US2-AS2, SC-004 |
| 4 | Past date, no snapshot | Run `XOM` with a date 2 years ago (provider `worldmonitor` or `snapshot`) | The geo panel shows the amber "unavailable for this date" note, `missing_inputs` contains `geo`, and confidence ≤ medium. No live data is used (check the logs: no live call) | US2-AS3, FR-009, Principle I |
| 5 | Forecast | Look at the Forecast panel on scenario 1 | Candles end at the analysis date, followed by the p50 line and the p10–p90 band. The stats show last close, expected move % and range | US3, FR-011/12 |
| 6 | Too little history | Run a recent IPO from the fixture set (`NEWIPO`) | The forecast panel shows "Not enough price history". The run still completes | US3-AS3, FR-004 |
| 7 | Geo source down | Set `GEOALPHA_GEO_PROVIDER=worldmonitor` with an invalid key → run | The geo stage fails after 1 automatic retry, with ErrorState and Retry. The run completes, and the decision notes the missing geo input | US1-AS4, FR-004/5 |
| 8 | Reload mid-run | Start a run, reload the page after 2 stages, then close the tab and reopen it from History | Progress is intact and the stream resumes (events replay from `last_event_seq`) | FR-006, edge case |
| 9 | Validation | Ticker `ZZZZZZ`, a future date | Inline errors appear, the Analyze button is disabled, and no run is created | FR-002, edge cases |
| 10 | Weekend date | Choose a Saturday | The header shows "Analysis date adjusted from Sat … to Fri …" | Edge case |
| 11 | Missing LLM key | Remove `ANTHROPIC_API_KEY`, restart, open `/` | An amber config banner appears before any run can start | Edge case |
| 12 | History | Complete 2 runs, then open `/history` | Newest first, with skeleton rows while loading. Opening the older run shows the full report in under 2 s | US4, FR-018/19, SC-007 |
| 13 | UI quality | Toggle dark mode, resize to 360px, navigate with only Tab and Enter, and enable OS reduced motion | Both themes are legible, there is no horizontal page scroll, focus rings are visible, and skeletons are static | FR-023/24, Principle III |

## Snapshot recorder (builds geopolitical history)

```powershell
cd backend; uv run geoalpha snapshot --watchlist XOM,CVX,LMT,TSM,GLD
```

Schedule it daily, for example with Windows Task Scheduler at 17:00 ET. Snapshots are immutable and
dated, so they become eligible point-in-time input for future runs and for the next feature
(backtesting).
