import { useState } from 'react'
import { Badge, Card, CardHeader, cn, EmptyState, focusRing, type Tone } from '../../components/ui'
import { AsyncRegion, type RegionStatus } from '../../components/ui/AsyncRegion'
import { Skeleton } from '../../components/ui/Skeleton'
import type { GeoSignal, RunDetail } from '../../lib/api'
import { formatDate, formatDateTime, relativeTime } from '../../lib/format'
import { getStage, stageError } from './stage-utils'

const impact: Record<GeoSignal['impact_direction'], { icon: string; label: string; tone: Tone }> = {
  positive: { icon: '↑', label: 'Tailwind', tone: 'positive' },
  negative: { icon: '↓', label: 'Headwind', tone: 'negative' },
  mixed: { icon: '↕', label: 'Mixed', tone: 'warning' },
  uncertain: { icon: '?', label: 'Unclear', tone: 'neutral' },
}

const pretty = (s: string) => s.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())

function SeverityDots({ value }: { value: number }) {
  return (
    <span className="inline-flex items-center gap-0.5" title={`Severity ${value} of 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span
          key={i}
          aria-hidden="true"
          className={cn('size-1.5 rounded-full', i <= value ? (value >= 4 ? 'bg-negative' : 'bg-warning') : 'bg-skeleton')}
        />
      ))}
      <span className="sr-only">Severity {value} of 5</span>
    </span>
  )
}

function SignalRow({ s }: { s: GeoSignal }) {
  const [open, setOpen] = useState(false)
  const im = impact[s.impact_direction]
  return (
    <li id={`signal-${s.id}`} tabIndex={-1} className="rounded-lg px-4 py-3 outline-none sm:px-5">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 w-5 shrink-0 text-center text-xs font-semibold text-muted">{s.rank}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <SeverityDots value={s.severity} />
            <Badge>{pretty(s.category)}</Badge>
            <span className="text-xs font-medium text-muted">{s.region.replace(/_/g, ' ')}</span>
          </div>
          <p className="mt-1 text-sm font-medium text-fg">{s.headline}</p>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
            <time dateTime={s.valid_at} title={formatDateTime(s.valid_at)}>
              {relativeTime(s.valid_at)}
            </time>
            {s.source_url ? (
              <a
                href={s.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className={cn('rounded text-accent hover:underline', focusRing)}
              >
                {s.source_label}
                <span className="sr-only"> (opens in a new tab)</span>
              </a>
            ) : (
              <span>{s.source_label}</span>
            )}
            <button
              type="button"
              aria-expanded={open}
              onClick={() => setOpen((v) => !v)}
              className={cn('rounded font-medium text-fg/80 hover:text-fg', focusRing)}
            >
              {open ? 'Hide why' : 'Why it matters'}
            </button>
          </div>
          {open && <p className="mt-2 rounded-md bg-surface-2 px-3 py-2 text-xs leading-relaxed text-fg">{s.rationale}</p>}
        </div>
        <Badge tone={im.tone} className="shrink-0">
          <span aria-hidden="true">{im.icon}</span>
          {im.label}
        </Badge>
      </div>
    </li>
  )
}

function GeoSkeleton() {
  return (
    <div>
      <div className="flex gap-2 border-b border-border px-4 py-3 sm:px-5">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-6 w-20" />
        ))}
      </div>
      <ul className="divide-y divide-border">
        {[0, 1, 2, 3, 4].map((i) => (
          <li key={i} className="flex gap-3 px-4 py-3 sm:px-5">
            <Skeleton className="h-4 w-5" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-3 w-40" />
            </div>
            <Skeleton className="h-5 w-20" />
          </li>
        ))}
      </ul>
    </div>
  )
}

export function GeoPanel({ run, onRetry }: { run: RunDetail; onRetry: () => void }) {
  const stage = getStage(run, 'geo')
  const geo = run.geo
  const status: RegionStatus =
    stage.status === 'failed'
      ? 'error'
      : geo
        ? geo.materiality === 'material' && geo.signals.length
          ? 'ready'
          : 'empty'
        : stage.status === 'skipped'
          ? 'empty'
          : stage.status === 'done' || run.status === 'failed' || run.status === 'interrupted'
            ? 'error'
            : 'loading'

  const empty =
    geo?.materiality === 'unavailable' ? (
      <EmptyState tone="warning" title="Geopolitical data unavailable for this date" description={geo.unavailable_reason ?? undefined} />
    ) : stage.status === 'skipped' ? (
      <EmptyState title="Not part of this run" />
    ) : (
      <EmptyState
        title={`No material geopolitical exposure detected for ${formatDate(run.analysis_date)}`}
        description="Signals were checked for the countries and routes this company depends on."
      />
    )

  return (
    <Card className="h-full">
      <CardHeader
        title="Geopolitical exposure"
        subtitle={geo?.signals.length ? `${geo.signals.length} signals, ranked by relevance to ${run.ticker}` : 'Signals relevant to this company, with sources'}
      />
      <AsyncRegion
        label="geopolitical signals"
        status={status}
        minHeightClass="min-h-96"
        timeoutMs={5 * 60_000}
        skeleton={<GeoSkeleton />}
        empty={empty}
        errorMessage={stageError(stage, run)}
        onRetry={onRetry}
      >
        {geo && (
          <div>
            {geo.exposure && (
              <div className="flex flex-wrap items-center gap-1.5 border-b border-border px-4 py-3 sm:px-5">
                <span className="mr-1 text-xs text-muted">Exposure</span>
                {(geo.exposure.countries ?? []).map((c) => (
                  <span key={c.iso2} title={c.reason} className="rounded-md border border-border px-1.5 py-0.5 text-xs">
                    {c.iso2} <span className="text-muted">{Math.round((c.weight ?? 0) * 100)}%</span>
                  </span>
                ))}
                {(geo.exposure.chokepoints ?? []).map((c) => (
                  <Badge key={c} tone="accent">
                    {pretty(c)}
                  </Badge>
                ))}
              </div>
            )}
            <ol className="divide-y divide-border">
              {geo.signals.map((s) => (
                <SignalRow key={s.id} s={s} />
              ))}
            </ol>
          </div>
        )}
      </AsyncRegion>
    </Card>
  )
}
