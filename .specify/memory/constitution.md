<!--
Sync Impact Report
- Version change: (template) → 1.0.0
- Modified principles: n/a (initial ratification)
- Added principles:
  I. Point-in-Time Integrity (NON-NEGOTIABLE)
  II. Explainable, Attributed Signals
  III. Clean Tailwind UI/UX
  IV. Skeleton-First Loading (NON-NEGOTIABLE)
  V. Test-Backed Changes
  VI. Simplicity & Composition Over Forking
- Added sections: Technology & Licensing Constraints; Development Workflow & Quality Gates; Governance
- Removed sections: none
- Templates: plan/spec/tasks templates read this file at runtime; no template edits required
- Deferred TODOs: none
-->

# GeoAlpha Constitution

GeoAlpha is a research tool that combines geopolitical intelligence (WorldMonitor),
candle-based price forecasting (Kronos), and multi-agent LLM trading analysis
(TradingAgents) to evaluate whether geopolitical signals add measurable alpha.

## Core Principles

### I. Point-in-Time Integrity (NON-NEGOTIABLE)

- Every analysis, forecast, and backtest MUST use only data that was published at or before
  the analysis timestamp. Look-ahead leakage is treated as a correctness bug, not a tuning issue.
- Live-only sources (e.g. WorldMonitor feeds) MUST be snapshotted with a capture timestamp
  before they are used in any historical evaluation; un-snapshotted live data MUST NOT enter
  a backtest.
- Every stored signal MUST carry `as_of` (when it was valid) and `captured_at` (when we
  recorded it) timestamps.

Rationale: a geopolitical edge that only exists because of leaked future data is worthless,
and the whole purpose of the project is to measure that edge honestly.

### II. Explainable, Attributed Signals

- Every recommendation shown to a user MUST link to the evidence behind it: the source of each
  geopolitical signal, the Kronos forecast (with its uncertainty band), and the agent debate
  transcript.
- Outputs MUST be labelled as research, not financial advice, and MUST show the model and
  provider used along with the run date.
- Non-determinism (LLM variance, sampled forecasts) MUST be surfaced rather than hidden,
  for example by showing sample spread or repeat-run disagreement.

Rationale: users must be able to tell *why* the system leaned a certain way, and when
it is unsure.

### III. Clean Tailwind UI/UX

- All styling MUST use Tailwind CSS utility classes and design tokens defined in the Tailwind
  config. No other CSS frameworks; hand-written CSS is limited to global base layers and
  keyframes.
- The visual language is minimalist and modern: generous whitespace, a restrained neutral
  palette with one accent colour plus semantic colours (positive, negative, warning), a single
  type scale, consistent radius and spacing scales, and no decorative clutter.
- Information hierarchy comes first: the primary number or decision in each view MUST be
  identifiable at a glance; secondary detail is revealed progressively (expandable panels,
  drawers, tabs).
- Every view MUST support light and dark mode, be responsive down to 360px wide with no
  horizontal page scroll, be keyboard navigable with visible focus rings, and meet WCAG 2.1 AA
  contrast.
- Reusable UI primitives (Card, Button, Badge, Stat, Table, Skeleton, EmptyState, ErrorState)
  MUST live in one shared component library; feature code composes them rather than restyling.

Rationale: dense financial and geopolitical data is only useful when it is calm and legible.

### IV. Skeleton-First Loading (NON-NEGOTIABLE)

- Every region that renders asynchronous data MUST display a skeleton placeholder that
  mirrors the final layout's shape and dimensions (cards, rows, chart area, text lines)
  while loading.
- Full-page or content-area spinners are prohibited; a small inline spinner is permitted only
  on buttons for user-triggered actions.
- Loading → loaded transitions MUST NOT cause layout shift (target CLS < 0.1).
- Skeleton shimmer/pulse animation MUST be disabled under `prefers-reduced-motion`.
- Every async region MUST also define explicit **empty** and **error** states (with retry);
  a skeleton MUST NOT remain visible indefinitely, so a timeout MUST transition to the error state.
- Long-running jobs (agent runs, backtests) MUST stream progress stage-by-stage, revealing
  completed sections while remaining sections stay in skeleton form.

Rationale: agent runs and model inference are slow; perceived performance and spatial
stability are what make the product feel trustworthy.

### V. Test-Backed Changes

- Data adapters, signal transforms, and point-in-time filters MUST have automated tests,
  including at least one explicit look-ahead regression test per data source.
- API contracts between backend and frontend MUST be typed and validated on both sides,
  with contract tests.
- UI components MUST be tested for their loading (skeleton), empty, error, and loaded states.
- External services (LLM providers, WorldMonitor, Hugging Face) MUST be mockable so the test
  suite runs offline and deterministically.

### VI. Simplicity & Composition Over Forking

- Upstream projects are consumed as dependencies or through their public APIs, SDKs, or MCP
  servers, never by copying or forking their source into this repo unless that is justified
  in a plan's Complexity Tracking table.
- New abstractions MUST be justified by a current need (YAGNI). Prefer one service and one web
  app until measured load proves otherwise.

## Technology & Licensing Constraints

- **Backend**: Python 3.11+, FastAPI, Pydantic models for every external and internal contract.
  TradingAgents and Kronos are used as Python libraries in-process or in a worker.
- **Frontend**: TypeScript (strict), React, Vite, Tailwind CSS. Server state goes through a
  query/caching layer that exposes loading, empty, and error states explicitly
  (to satisfy Principle IV).
- **Licensing**: WorldMonitor is AGPL-3.0. GeoAlpha MUST consume it only through its
  public API, SDK, or MCP server and MUST NOT vendor or modify its source. Upstream licences
  MUST be recorded in `THIRD_PARTY_LICENSES.md`.
- **Secrets**: API keys come from environment variables only; `.env` files MUST NOT be committed.
- **Safety**: GeoAlpha MUST NOT place live orders. Any future execution capability requires a
  constitution amendment.

## Development Workflow & Quality Gates

- Work follows Spec Kit: `/speckit-specify` → (`/speckit-clarify`) → `/speckit-plan` →
  `/speckit-tasks` → (`/speckit-analyze`) → `/speckit-implement`, one feature branch per spec.
- Every plan MUST include a Constitution Check covering all six principles; violations go in
  Complexity Tracking with a justification or are removed.
- A change is merge-ready only when tests pass, types check, linting is clean, and every new
  async UI region has been visually checked in its skeleton, empty, error, and loaded states
  in both light and dark mode.

## Governance

- This constitution supersedes other project practices. Where guidance conflicts,
  this document wins.
- Amendments require: a written rationale, a version bump, an updated Sync Impact Report,
  and review of dependent specs and plans for impact.
- Versioning: MAJOR for removing or redefining a principle; MINOR for a new principle or
  section, or materially expanded guidance; PATCH for clarifications.
- Reviews of every spec, plan, and pull request MUST verify compliance, with Principles I and IV
  checked explicitly.

**Version**: 1.0.0 | **Ratified**: 2026-11-02 | **Last Amended**: 2026-11-02
