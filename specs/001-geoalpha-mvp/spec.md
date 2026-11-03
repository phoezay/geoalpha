# Feature Specification: GeoAlpha MVP: Geopolitically-Aware Ticker Analysis

**Feature Branch**: `001-geoalpha-mvp`

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "GeoAlpha MVP: pick a ticker and date, and get a TradingAgents decision
with an added Geopolitical Analyst (WorldMonitor) and a Kronos price forecast, shown in a clean
Tailwind dashboard where each section loads with a skeleton."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a geopolitically-aware analysis and get a decision (Priority: P1)

A market researcher enters a ticker (e.g. XOM) and an analysis date, then starts an analysis.
The dashboard immediately shows the layout of the final report as skeleton placeholders.
As each stage finishes (geopolitical analyst, the other analysts, the bull/bear debate,
trader, risk review, and final decision), its section replaces its skeleton in place. The run
ends with a final rating (Buy / Overweight / Hold / Underweight / Sell), a confidence indication
and a short rationale that explicitly cites the geopolitical factors considered.

**Why this priority**: This is the core value proposition: a trading decision that has
reasoned about geopolitical risk. Without it there is no product.

**Independent Test**: Enter a supported ticker and a past date, start a run, and verify that
a final rating with rationale appears, that the rationale references at least one geopolitical
factor or explicitly states none were material, and that every section showed a skeleton before
its content.

**Acceptance Scenarios**:

1. **Given** the start screen, **When** the user enters a valid ticker and date and starts a
   run, **Then** within 1 second a skeleton of the full report layout is shown and a progress
   indicator lists all stages with their status (pending / running / done / failed).
2. **Given** a run in progress, **When** a stage completes, **Then** only that section swaps
   from skeleton to content, without shifting the position of other sections.
3. **Given** a completed run, **When** the user views the decision, **Then** they see the
   rating, a confidence indication, a rationale, the model/provider used, the analysis date,
   and a "research, not financial advice" label.
4. **Given** a run in progress, **When** one non-critical stage fails (e.g. the geopolitical
   source is unreachable), **Then** that section shows an error state with retry, the run
   still completes, and the decision states that this input was missing.

---

### User Story 2 - Inspect the geopolitical exposure behind the decision (Priority: P2)

The researcher opens the Geopolitical panel to see which geopolitical signals were judged
relevant to the ticker (e.g. regional conflict escalation, shipping-lane disruption, sanctions,
country instability for countries where the company has material exposure), how each was
scored, and links to the underlying sources.

**Why this priority**: Explainability is required by the constitution. Users must be able to
verify *why* geopolitics moved the decision before trusting it.

**Independent Test**: For a completed run, open the Geopolitical panel and verify each listed
signal shows its region, category, severity, direction of impact on the ticker, the time it
was valid, and a working source link.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the user opens the Geopolitical panel, **Then** they see
   a ranked list of relevant signals with region, category, severity, expected impact direction
   and source attribution.
2. **Given** a completed run where no material geopolitical signals were found, **When** the
   user opens the panel, **Then** a clear empty state explains that no material exposure was
   detected for that date.
3. **Given** a past analysis date with no recorded geopolitical snapshot, **When** the run
   executes, **Then** the panel states that geopolitical data is unavailable for that date
   instead of substituting current data.

---

### User Story 3 - See the model price forecast (Priority: P3)

The researcher views a chart of recent price history for the ticker followed by the model's
forecast path for the next period, with an uncertainty band, and sees that the agents were
given this forecast as one input among many.

**Why this priority**: The quantitative forecast adds an independent, non-LLM viewpoint and
is valuable on its own, but the decision is still useful without it.

**Independent Test**: For a completed run, verify the chart shows historical candles up to
the analysis date and a forecast path with a visible uncertainty band beyond it, and that
the forecast summary (expected move and range) appears in the agents' evidence.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the user views the Forecast panel, **Then** they see
   history up to the analysis date, a forecast path, an uncertainty band, and a numeric summary
   (expected % move and range over the horizon).
2. **Given** the chart is loading, **When** the user looks at the panel, **Then** a skeleton
   with the same dimensions as the chart is shown.
3. **Given** insufficient price history for the ticker, **When** the run executes, **Then**
   the Forecast panel shows an explanatory empty state and the decision notes the forecast
   was unavailable.

---

### User Story 4 - Revisit past runs (Priority: P4)

The researcher opens a history list of previous runs (ticker, date, rating, run time) and
opens any of them to see the full saved report without re-running it.

**Why this priority**: Runs are slow and cost LLM usage, so reviewing past results without
re-running them saves time and money, but this is not essential for a first demo.

**Independent Test**: Complete two runs, reload the application, open the history list, and
open the earlier run. Verify that its full report shows identical content.

**Acceptance Scenarios**:

1. **Given** at least one completed run, **When** the user opens History, **Then** runs are
   listed newest first with ticker, analysis date, rating and completion time.
2. **Given** the history list is loading, **When** the user views it, **Then** skeleton rows
   matching the row layout are shown.
3. **Given** no runs exist, **When** the user opens History, **Then** an empty state invites
   them to start their first analysis.

---

### User Story 5 - Export a report (Priority: P5)

From a completed run, the researcher downloads the full report as a Markdown file or as a
single self-contained HTML page, to share or archive outside the app.

**Why this priority**: Every community TradingAgents GUI offers export, and users expect it.
But it adds nothing to the analysis itself, so it comes last.

**Independent Test**: Open a completed run, export it as Markdown and as HTML, and verify that
both files open offline and contain the rating, confidence, rationale, geopolitical signals with
sources, forecast summary, all analyst reports, the model/date metadata and the disclaimer.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the user chooses Export → Markdown or Export → HTML,
   **Then** a file named `{ticker}_{analysis_date}_{run_id}.{md|html}` downloads.
2. **Given** a run that is not completed, **When** the user views the report, **Then** export
   is disabled and a tooltip explains why.

### Edge Cases

- Unknown or unsupported ticker → inline validation message before a run starts; no run created.
- Analysis date in the future, or a non-trading day → future dates rejected; non-trading days
  roll back to the previous trading session, and this adjustment is shown to the user.
- User navigates away or reloads mid-run → the run continues and can be reopened with its
  current progress.
- A stage hangs → after its timeout the section shows an error state with retry, never an
  endless skeleton.
- Two runs for the same ticker and date → both are kept as separate runs; nothing is silently
  overwritten.
- Language-model provider credentials missing or invalid → a clear configuration error is
  shown before the run starts.
- Reduced-motion preference enabled → skeletons render without animation.

## Requirements *(mandatory)*

### Functional Requirements

**Run lifecycle**

- **FR-001**: Users MUST be able to start an analysis by providing a ticker symbol and an
  analysis date (defaulting to the most recent completed trading day).
- **FR-002**: The system MUST validate the ticker and date before starting a run and reject
  future dates.
- **FR-003**: The system MUST execute the analysis as a sequence of named stages and report
  each stage's status (pending, running, done, failed) to the user in real time.
- **FR-004**: The system MUST continue a run when a non-critical input stage (geopolitical
  analysis or price forecast) fails, and MUST record in the decision which inputs were missing.
- **FR-005**: Each stage MUST have a timeout after which it is marked failed and can be retried
  individually.
- **FR-006**: Runs MUST continue in the background independent of the user's browser session
  and be reopenable while in progress or after completion.

**Geopolitical analysis**

- **FR-007**: The system MUST include a Geopolitical Analyst stage that gathers geopolitical
  signals (conflict, instability, sanctions, supply-route disruption, commodity and energy
  shocks) and assesses their relevance to the ticker's business exposure.
- **FR-008**: Each geopolitical signal shown MUST include region, category, severity,
  expected impact direction on the ticker, the time it was valid, and its source.
- **FR-009**: The system MUST only use geopolitical data valid at or before the analysis date.
  For past dates without recorded data, the stage MUST report "unavailable for this date"
  rather than use current data.
- **FR-010**: The system MUST record each geopolitical signal it captures, with the time it was
  valid and the time it was captured, so it can be used in future historical analyses.

**Price forecast**

- **FR-011**: The system MUST produce a price forecast for the ticker over a defined horizon
  using only price history up to the analysis date.
- **FR-012**: The forecast MUST include a central path, an uncertainty band, and a numeric
  summary (expected % move and range).
- **FR-013**: The forecast summary MUST be provided to the decision-making agents as evidence.

**Decision & explainability**

- **FR-014**: The final output MUST include a five-level rating, a confidence indication, and a
  rationale that references the geopolitical and forecast evidence it relied on (or states
  that the evidence was absent or immaterial).
- **FR-015**: Users MUST be able to view the full bull/bear debate and each analyst report
  that fed the decision.
- **FR-016**: Every report MUST display the analysis date, run time, model and provider used,
  and a "research, not financial advice" label.
- **FR-017**: The system MUST NOT place, or offer to place, any real trade.

**History**

- **FR-018**: The system MUST persist every run (inputs, stage outputs, decision, metadata)
  and list them newest first.
- **FR-019**: Users MUST be able to open any past run and view its full report without
  re-running it.

**Export**

- **FR-025**: Users MUST be able to export a completed run as Markdown and as a self-contained
  HTML file that includes all report content, sources, metadata and the disclaimer.

**Interface & loading experience**

- **FR-020**: Every area that loads data asynchronously MUST show a skeleton placeholder
  matching the shape and size of its final content while loading; content areas MUST NOT use
  spinners.
- **FR-021**: Swapping a skeleton for its content MUST NOT shift the position of surrounding
  content.
- **FR-022**: Every asynchronous area MUST define distinct loading, empty, error (with retry),
  and loaded states.
- **FR-023**: The interface MUST follow a clean, minimal visual design with one accent colour,
  support light and dark modes, work at widths down to 360px without horizontal scrolling,
  and be fully keyboard operable.
- **FR-024**: Skeleton animations MUST be disabled when the user prefers reduced motion.

### Key Entities

- **Analysis Run**: One request to analyse a ticker on a date. It holds the ticker, analysis
  date, created time, overall status, model and provider settings, and an ordered list of
  Stages, and has one Decision when complete.
- **Stage**: One named step of a run (e.g. Geopolitical Analyst, Market Analyst, Debate, Trader,
  Risk, Decision). It holds a status, start and end times, an output report, and an error if
  it failed.
- **Geopolitical Signal**: An observation about a region and category with a severity, valid-at
  time, captured-at time, source reference, and, per run, an assessed relevance and impact
  direction for the ticker.
- **Price Forecast**: For a run, the history window used, the horizon, the central path,
  the uncertainty band, and a summary (expected % move and range).
- **Decision**: The final rating, confidence, rationale, list of evidence used, and list of
  missing inputs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users see the full report skeleton within 1 second of starting a run, every
  time.
- **SC-002**: A complete analysis for a supported ticker finishes within 10 minutes in at
  least 90% of runs.
- **SC-003**: Visible layout shift on the report page stays below 0.1 (cumulative layout
  shift) from first skeleton to completed report.
- **SC-004**: 100% of decisions either cite at least one geopolitical signal with its source
  or explicitly state that none were material or available.
- **SC-005**: 0 instances in automated tests where a run uses geopolitical or price data
  that became available after the analysis date.
- **SC-006**: A first-time user can start an analysis and find the final rating and its
  geopolitical reasons in under 2 minutes of interaction, without guidance.
- **SC-007**: Past runs open with full content in under 2 seconds.

## Assumptions

- **Users**: a single researcher or a small trusted team running the tool locally or on a
  private host; no user accounts or authentication in the MVP.
- **Coverage**: US-listed equities and ETFs, matching the coverage of the existing
  multi-agent framework's data sources. Crypto, FX and non-US listings are out of scope for
  the MVP.
- **Geopolitical history**: the geopolitical source provides current data only. Point-in-time
  history therefore starts the day GeoAlpha begins recording, so analyses for earlier dates
  run without geopolitical input and say so explicitly.
- **Forecast horizon**: daily bars, with a default horizon of 5 trading days.
- **Language model access**: the operator supplies their own language-model provider
  credentials. Cost per run is the operator's responsibility.
- **Out of scope for this feature**: multi-ticker backtesting and alpha measurement (planned
  as the next feature), alerts, portfolio views, and any trade execution.
- **Dependencies**: WorldMonitor (geopolitical intelligence, consumed through its public
  interface only, due to AGPL-3.0), Kronos (open pre-trained forecasting model), and
  TradingAgents (multi-agent decision framework).
