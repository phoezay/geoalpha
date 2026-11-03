# UI Contract: Views, Async Regions and Their States

Implements Constitution III and IV and spec FR-020 to FR-024. Every async region below MUST render
through the shared `<AsyncRegion>` primitive and MUST pass the four-state component test
(loading, empty, error, loaded).

## Design tokens (Tailwind v4 `@theme`)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--color-bg` | `neutral-50` | `neutral-950` | page background |
| `--color-surface` | `white` | `neutral-900` | cards |
| `--color-border` | `neutral-200` | `neutral-800` | 1px card/table borders |
| `--color-muted` | `neutral-600` | `neutral-400` | secondary text (600 in light: 500 failed AA on surface-2 badges) |
| `--color-accent` | `indigo-600` | `indigo-300` | the single accent: primary button, focus ring, links, p50 line |
| `--color-positive` | `emerald-700` | `emerald-400` | Buy/Overweight, positive impact |
| `--color-negative` | `rose-700` | `rose-300` | Sell/Underweight, negative impact |
| `--color-warning` | `amber-700` | `amber-400` | missing inputs, unavailable |
| `--color-skeleton` | `neutral-200` | `neutral-800` | skeleton blocks |

Radius: `rounded-xl` for cards, `rounded-md` for controls. Spacing scale: 4/8/12/16/24/32. Type: Inter
(`text-sm` body, `text-xs` meta, `text-2xl font-semibold` for the primary stat). Focus:
`focus-visible:ring-2 ring-accent ring-offset-2`. Rating colours always come with the text
label (never colour alone).

## Shared primitives (`frontend/src/components/ui/`)

`Card`, `Button` (variants: primary, secondary, ghost; inline spinner allowed **only** here),
`Badge`, `Stat`, `Table`, `Tabs`, `Drawer`, `Skeleton`, `SkeletonText(lines)`, `EmptyState`,
`ErrorState(onRetry)`, `AsyncRegion`, `ThemeToggle`, `Disclaimer`.

### `<AsyncRegion>` behaviour

```text
props: status: 'loading'|'empty'|'error'|'ready', skeleton, empty, error, onRetry, timeoutMs, minHeightClass
- loading → renders `skeleton` inside a container with the same minHeightClass as the ready state
            container has aria-busy="true" plus an sr-only "Loading <label>…"
- loading for > timeoutMs → switches to error ("Taking longer than expected") with Retry
- empty   → EmptyState with a message and an optional call to action
- error   → ErrorState with a user-facing message and a Retry button (onRetry)
- ready   → children. The container keeps minHeightClass, so there is no layout shift
```

Skeleton blocks: `animate-pulse motion-reduce:animate-none bg-[--color-skeleton] rounded-md`,
`aria-hidden="true"`.

## Views

### `/`: New analysis

| Region | Async? | Skeleton | Empty | Error |
|---|---|---|---|---|
| Config banner (from `/api/health`) | yes | **none**: hidden while loading and when all is OK. Reserving h-10 would collapse in the common case and cause the very shift Principle IV forbids | hidden when all OK | amber banner listing `problems` (edge case: missing LLM credentials); a rose banner with Retry if the server is unreachable |
| Ticker field inline validation | yes | none (debounced 300 ms). Field shows a muted "Checking…" text | n/a | inline message under the field |
| Recent runs (last 5) | yes | 5 rows × h-12 | "No analyses yet. Start your first above." | ErrorState |

The form has a ticker field (auto-uppercased), a date field (defaults to the last session; future
dates disabled), and a primary "Analyze" button. On submit the app navigates **immediately** to
`/runs/:id` (SC-001).

### `/runs/:id`: Run report

Layout: a header row, then a 12-column grid (`lg:grid-cols-12`) that becomes 1 column below `lg`.

| Region | Grid | Fixed size | Skeleton shape | Empty / unavailable | Error |
|---|---|---|---|---|---|
| Header: ticker, analysis date (+ "adjusted from …" note), status badge, model/provider, Disclaimer | full | h-20 | title bar + 3 pills | n/a | n/a |
| Stage progress rail (10 stages) | full | h-14 (horizontal on lg, scrollable chips on mobile; the chip row may scroll horizontally, the page may not) | 10 pill outlines | n/a | failed stage chip in rose with Retry |
| **Decision card** | lg:col-span-12 | min-h-48 | big stat block + 3 text lines + 2 badges | n/a | ErrorState + Retry |
| Geopolitical panel | lg:col-span-7 | min-h-96 | 5 signal rows (badge + 2 lines) | **immaterial**: "No material geopolitical exposure detected for {date}". **unavailable**: amber note "Geopolitical data unavailable for this date" + reason | ErrorState + Retry |
| Forecast panel | lg:col-span-5 | chart `aspect-[16/10]` + stats h-16 | grey chart box + 3 stat blocks | **unavailable**: "Not enough price history to forecast" | ErrorState + Retry |
| Analyst reports (Tabs: Market, Sentiment, News, Fundamentals) | lg:col-span-12 | min-h-64 | tab bar + 6 text lines | "This analyst was not part of the run" | per-tab ErrorState |
| Debate (Bull/Bear turns + Research Manager verdict) | lg:col-span-6 | min-h-64 | 3 alternating bubbles | n/a | ErrorState |
| Trader & Risk review | lg:col-span-6 | min-h-64 | 4 text blocks | n/a | ErrorState |

Each region swaps from skeleton to content **independently**, driven by its stage's status from
SSE (FR-003, US1-AS2). The decision card shows the rating as a coloured `Stat` with its label,
a confidence badge, the summary, cited signals as chips (clicking one scrolls to the geo row and
highlights it), forecast-alignment text, and a "Missing inputs" amber note when
`missing_inputs` is non-empty (US1-AS4).

Geo signal row: severity dots (1–5), category badge, region, headline, impact arrow
(↑ positive / ↓ negative / ↕ mixed / ? uncertain, with a text label), `valid_at` relative time,
and a source link (opens in a new tab, `rel="noopener noreferrer"`).
Expanding a row reveals the rationale (progressive disclosure).

Forecast chart: candlesticks (history), dashed accent p50 line, and an accent band at 15%
opacity between p10 and p90 for the forecast range, with a vertical divider at the analysis
date. Stats: Last close · Expected move (±%) · Range p10–p90.

### `/history`: Past runs

| Region | Skeleton | Empty | Error |
|---|---|---|---|
| Runs table (ticker, analysis date, rating badge, status, finished) | 8 rows × h-12, same column widths | "No runs yet" + "Start an analysis" button | ErrorState |

Rows are links to `/runs/:id`. Pagination uses a "Load more" button (skeleton rows are appended
while loading). On mobile, the table becomes stacked cards (no horizontal page scroll).

## Global rules (tested)

1. No spinner inside any content region. A `role="progressbar"` or spinner may only appear inside `Button`.
2. CLS < 0.1 from the first skeleton to the completed report (Playwright e2e, SC-003).
3. Under `prefers-reduced-motion: reduce`, there are no animated elements (e2e checks computed `animation-name: none` on skeletons).
4. Light and dark themes both pass axe with no serious or critical violations. Contrast meets WCAG AA.
5. At a 360px viewport, `document.scrollingElement.scrollWidth ≤ 360`.
6. Every interactive element is reachable by Tab, with a visible focus ring.
