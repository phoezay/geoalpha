# Data Model: GeoAlpha MVP

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

All timestamps are stored in UTC (ISO-8601). "Date" fields are US-market session dates
(America/New_York). IDs are ULIDs (sortable, so the history list orders newest first by ID).

---

## AnalysisRun

One request to analyse a ticker on a date (spec: *Analysis Run*).

| Field | Type | Rules |
|---|---|---|
| `id` | ULID | PK |
| `ticker` | str | Upper-case, `^[A-Z][A-Z0-9.\-]{0,9}$`, and must resolve to a US-listed equity or ETF (FR-002) |
| `requested_date` | date | What the user entered. Must be ≤ today ET (FR-002) |
| `analysis_date` | date | `requested_date` rolled back to the previous NYSE session if it is not one (edge case). Shown to the user when it differs |
| `status` | enum | `queued` → `running` → `completed` / `failed` / `interrupted` (see transitions) |
| `created_at`, `started_at`, `finished_at` | datetime? | `finished_at` is set on reaching any terminal state |
| `llm_provider`, `deep_model`, `quick_model` | str | Snapshot of the config used (FR-016) |
| `settings` | JSON | Other run settings: debate rounds, forecast horizon, sample count, geo provider mode |
| `retry_of` | ULID? | FK → AnalysisRun. Set for "Re-run with fresh inputs" (research R3) |
| `missing_inputs` | list[`geo`\|`forecast`] | Filled when a non-critical stage ends `failed` or `unavailable` (FR-004) |
| `error` | str? | Top-level failure message when `status=failed` |

**Relationships**: 1 → N `Stage` (fixed set, created up front); 1 → 0..1 `PriceForecast`;
1 → N `RunGeoSignal`; 1 → 0..1 `Decision`; 1 → N `RunEvent`.

**State transitions**

```text
queued ──start──▶ running ──all stages terminal & decision saved──▶ completed
                     │
                     ├──critical stage failed/timeout──▶ failed ──retry (resume checkpoint)──▶ running
                     └──server restart while running──▶ interrupted ──retry──▶ running
```

`completed` is final: a completed run is never mutated. Re-runs create a new run linked by `retry_of`.

---

## Stage

One named step of a run (spec: *Stage*). All 10 rows are created when the run is created,
so the UI can draw the full skeleton immediately (SC-001).

| Field | Type | Rules |
|---|---|---|
| `run_id` | ULID | FK, part of the composite PK |
| `key` | enum | See *Stage keys* below. Part of the composite PK |
| `order` | int | Display order |
| `critical` | bool | `false` for `geo` and `forecast`, `true` for all others |
| `status` | enum | `pending` → `running` → `done` / `failed` / `unavailable` / `skipped` |
| `started_at`, `finished_at` | datetime? | |
| `timeout_s` | int | geo 120, forecast 180, TA stages 600, decision_card 90 |
| `report_md` | text? | Human-readable stage output (markdown) |
| `payload` | JSON? | Structured stage output (e.g. debate turns), as given by the contracts |
| `error` | str? | User-facing message. Technical details go to logs only |
| `attempts` | int | Incremented per attempt |

`unavailable` means the input legitimately does not exist (no snapshot for that date, too
little price history). This differs from `failed`, which means an error or timeout.
`skipped` is used for stages not configured in the run settings.

### Stage keys

| key | Label (UI) | Producer | Upstream node(s) mapped |
|---|---|---|---|
| `geo` | Geopolitical Analyst | GeoAlpha | n/a |
| `forecast` | Price Forecast | GeoAlpha (Kronos) | n/a |
| `market` | Market Analyst | TradingAgents | `Market Analyst` |
| `sentiment` | Sentiment Analyst | TradingAgents | `Sentiment Analyst` |
| `news` | News Analyst | TradingAgents | `News Analyst` |
| `fundamentals` | Fundamentals Analyst | TradingAgents | `Fundamentals Analyst` |
| `research_debate` | Bull vs Bear Debate | TradingAgents | `Bull Researcher`, `Bear Researcher`, `Research Manager` |
| `trader` | Trader | TradingAgents | `Trader` |
| `risk_debate` | Risk Review | TradingAgents | `Aggressive Analyst`, `Conservative Analyst`, `Neutral Analyst` |
| `decision` | Final Decision | TradingAgents + GeoAlpha | `Portfolio Manager`, then GeoAlpha `decision_card` |

A multi-node stage is `running` from the first node starting until its last node finishes.

---

## GeoSnapshot

Raw WorldMonitor responses as captured (FR-010; Constitution I).

| Field | Type | Rules |
|---|---|---|
| `id` | ULID | PK |
| `tool` | str | e.g. `get_country_risk`, `get_conflict_events`, `get_world_brief` |
| `params_hash` | str | SHA-256 of canonical JSON params (lookup key) |
| `params` | JSON | |
| `payload` | JSON | Response after jmespath projection |
| `as_of` | date | Session date the data is considered valid for |
| `captured_at` | datetime | When GeoAlpha fetched it. **Immutable** |
| `source_mode` | enum | `hosted` / `self_hosted` / `fixture` |

**Index**: `(tool, params_hash, captured_at DESC)`.
**Eligibility rule** for analysis date D (research R4): if D is the current session (today ET or the latest completed session), fetch live and save.
Otherwise use the latest snapshot with `D−3d ≤ captured_at ≤ D 23:59:59 ET`. If there is none,
the stage is `unavailable`.

---

## ExposureProfile

The countries, commodities and chokepoints a ticker is exposed to. Cached per ticker and quarter.

| Field | Type | Rules |
|---|---|---|
| `ticker` | str | PK part |
| `quarter` | str | `YYYYQn` of `analysis_date`. PK part |
| `countries` | list[{`iso2`, `weight` 0–1, `reason`}] | 1–6 entries. Weights sum to ≤ 1 |
| `commodities` | list[str] | e.g. `crude_oil`, `lng`, `semiconductors` |
| `chokepoints` | list[str] | e.g. `strait_of_hormuz`, `red_sea`, `taiwan_strait` |
| `themes` | list[str] | Free text, ≤ 5 |
| `created_at` | datetime | |

---

## GeoSignal and RunGeoSignal

*GeoSignal* (spec entity) is stored per run, because relevance and impact are assessments
specific to that run.

| Field | Type | Rules |
|---|---|---|
| `id` | str | `run_id:n` (stable citation ID for the decision card) |
| `run_id` | ULID | FK |
| `rank` | int | 1 = most relevant. At most 10 per run |
| `region` | str | ISO2 country or a named region / chokepoint |
| `category` | enum | `conflict`, `instability`, `sanctions`, `supply_route`, `commodity_shock`, `energy`, `cyber`, `disaster`, `policy`, `other` |
| `severity` | int | 1–5 |
| `impact_direction` | enum | `positive` / `negative` / `mixed` / `uncertain` |
| `headline` | str | ≤ 140 chars |
| `rationale` | str | Why it matters for *this* ticker |
| `valid_at` | datetime | From the source payload, or the snapshot's `captured_at` |
| `snapshot_id` | ULID | FK → GeoSnapshot. **Required** (no unsourced signals, Constitution II) |
| `source_label`, `source_url` | str, str? | Human attribution and link if the payload has one (FR-008) |

Run-level geo summary on the `geo` stage `payload`: `{geo_materiality: material|immaterial|unavailable, exposure_profile_ref, signal_count}`.

---

## PriceForecast

| Field | Type | Rules |
|---|---|---|
| `run_id` | ULID | PK/FK |
| `model` | str | e.g. `NeoQuasar/Kronos-small` |
| `history` | list[{`date`, `open`, `high`, `low`, `close`, `volume`}] | Last 120 bars shown in the chart. **All `date ≤ analysis_date`** |
| `lookback_bars` | int | Bars fed to the model (≤ 400) |
| `horizon` | int | Default 5 sessions |
| `path` | list[{`date`, `p10`, `p50`, `p90`}] | Length = horizon. `p10 ≤ p50 ≤ p90` |
| `sample_count` | int | Default 30 |
| `last_close` | float | |
| `expected_move_pct` | float | `(p50[h] / last_close − 1) × 100` |
| `range_low`, `range_high` | float | `p10[h]`, `p90[h]` |

---

## Decision

| Field | Type | Rules |
|---|---|---|
| `run_id` | ULID | PK/FK |
| `rating` | enum | `Buy` / `Overweight` / `Hold` / `Underweight` / `Sell` (from TradingAgents `PortfolioRating`) |
| `confidence` | enum | `low` / `medium` / `high`. Capped at `medium` when `missing_inputs` is non-empty |
| `summary` | str | ≤ 600 chars, plain language |
| `rationale_md` | text | Full Portfolio Manager decision text |
| `geo_statement` | enum | `cites` / `none_material` / `unavailable` |
| `cited_signal_ids` | list[str] | Non-empty **iff** `geo_statement = cites` (SC-004 validator) |
| `forecast_alignment` | enum | `supports` / `contradicts` / `neutral` / `unavailable` |
| `missing_inputs` | list[str] | Copied from the run |
| `disclaimer` | const | "Research output, not financial advice." (FR-016) |

---

## RunEvent

Append-only progress log that backs the SSE stream (research R8).

| Field | Type | Rules |
|---|---|---|
| `seq` | int | Per-run monotonic, used as the SSE `id` (`Last-Event-ID` replay) |
| `run_id` | ULID | FK |
| `type` | enum | See [contracts/sse-events.schema.json](./contracts/sse-events.schema.json) |
| `data` | JSON | Event payload |
| `at` | datetime | |

---

## Validation summary (FR → rule)

| Requirement | Enforced where |
|---|---|
| FR-002 | `RunCreate` validator: ticker regex + resolver, `requested_date ≤ today ET` |
| FR-004 | The orchestrator treats `geo`/`forecast` failure as non-fatal and writes `missing_inputs` |
| FR-005 | Per-stage `timeout_s`. Retry endpoint (critical stages resume from checkpoint) |
| FR-008 | `RunGeoSignal` requires `snapshot_id`, `source_label`, `valid_at` |
| FR-009 / SC-005 | `GeoSnapshot` eligibility rule. The price source filters `date ≤ analysis_date` |
| FR-012 | `PriceForecast` checks `p10 ≤ p50 ≤ p90` and length = horizon |
| FR-014 / SC-004 | `Decision` checks the `geo_statement` and `cited_signal_ids` pairing |
| FR-016 | Model fields on the run plus a constant disclaimer on `Decision` |
