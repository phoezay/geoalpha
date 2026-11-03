# GeoAlpha

**Trading research that weighs geopolitical risk and shows its evidence.**

You enter a US ticker and a date. GeoAlpha runs a multi-agent LLM trading committee
([TradingAgents](https://github.com/TauricResearch/TradingAgents)) with two extra inputs:

- **Geopolitical signals** from [WorldMonitor](https://github.com/koala73/worldmonitor), filtered
  to the countries, commodities and shipping routes the company actually depends on.
- **A price forecast** from [Kronos](https://github.com/shiyu-coder/Kronos), a foundation model
  for candlestick data, with an 80% uncertainty band.

The report streams in stage by stage. Each section shows a skeleton until its stage finishes,
then fills in without moving anything else. The final rating comes with a confidence level, the
specific geopolitical signals it relied on (each with a link to its source), and the full debate
between the analysts.

> Research output, not financial advice. GeoAlpha never places trades.

## Quick start (no API keys needed)

Demo mode runs the whole app offline. It uses a scripted committee, labelled demo geopolitical
data and the real Kronos model (weights download from Hugging Face on first use).

Prerequisites: [`uv`](https://docs.astral.sh/uv/) ≥ 0.12, Node.js ≥ 22.

```powershell
cp .env.example .env                       # demo defaults: GEOALPHA_ENGINE=fake, GEO_PROVIDER=fixture
cd backend;  uv sync;  uv run geoalpha serve        # API on http://127.0.0.1:8000
cd frontend; npm install; npm run dev               # UI on  http://127.0.0.1:5173
```

Open http://127.0.0.1:5173 and analyse `XOM`, `LMT`, `TSM`, `GLD` or `KO`. `NEWIPO` shows the
"not enough history" path, and `FAILME` shows failure and resume.

## Real analyses

Set these in `.env`:

| Setting | Values |
|---|---|
| `GEOALPHA_ENGINE` | `tradingagents` to run the real agent committee |
| `TRADINGAGENTS_LLM_PROVIDER` + key | Default `anthropic` with `ANTHROPIC_API_KEY`. Any provider TradingAgents supports works |
| `TRADINGAGENTS_DEEP_THINK_LLM` / `_QUICK_THINK_LLM` | Default `claude-opus-5-5` / `claude-sonnet-5` |
| `GEOALPHA_GEO_PROVIDER` | `fixture` (demo data), `worldmonitor` (live), or `snapshot` (recorded data only) |

**WorldMonitor access** (only for `worldmonitor`). Choose one:

- **Hosted:** `WORLDMONITOR_API_KEY`. Data tools need a WorldMonitor Pro plan.
- **Self-hosted:** run WorldMonitor's Docker stack (see its `SELF_HOSTING.md`), then set
  `WORLDMONITOR_BASE_URL`, `WORLDMONITOR_MCP_URL` and an operator key. It's free, and most feeds
  need no key or only free signups.

A real run makes roughly 12–20 LLM calls and typically takes a few minutes. The report header
shows the provider and models used.

## Point-in-time data

An analysis only uses data that existed on its date. WorldMonitor provides live data only, so:

- Runs for the **current session** fetch live data and save each response as a dated snapshot.
- Runs for **earlier dates** use snapshots recorded by then. If none exist, the geopolitical
  section says "unavailable for this date" instead of quietly using today's data.

To build history for backtesting, record snapshots daily (for example with Task Scheduler at
17:00 ET):

```powershell
cd backend; uv run geoalpha snapshot --watchlist XOM,CVX,LMT,TSM,GLD
```

## Development

The project follows [Spec Kit](https://github.com/github/spec-kit). The governing documents
live in [`.specify/memory/constitution.md`](.specify/memory/constitution.md) and
[`specs/001-geoalpha-mvp/`](specs/001-geoalpha-mvp/) (spec, plan, research, data model,
contracts, tasks).

```powershell
cd backend;  uv run pytest; uv run ruff check; uv run mypy        # unit, contract, look-ahead tests
cd backend;  uv run pytest -m integration                         # real Kronos (downloads weights)
cd frontend; npm run typecheck; npm run lint; npm test            # four-state component tests
cd frontend; npm run e2e                                          # Playwright: flow, CLS, a11y, 360px
```

| Layer | Stack |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy/SQLite, Server-Sent Events, TradingAgents 0.7.1 (extended by subclass, not forked), vendored Kronos, worldmonitor-sdk |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS v4, TanStack Query, lightweight-charts |

Licences: see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). WorldMonitor (AGPL-3.0) is only
called over the network. None of its code is included.
