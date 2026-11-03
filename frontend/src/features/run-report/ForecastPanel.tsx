import { lazy, Suspense } from 'react'
import { Card, CardHeader, EmptyState, Stat } from '../../components/ui'
import { AsyncRegion, type RegionStatus } from '../../components/ui/AsyncRegion'
import { Skeleton } from '../../components/ui/Skeleton'
import type { RunDetail } from '../../lib/api'
import { getStage, stageError } from './stage-utils'

const ForecastChart = lazy(() => import('./ForecastChart').then((m) => ({ default: m.ForecastChart })))

/** Mirrors the loaded layout box for box (chart, stats row, note) so nothing shifts. */
function ChartSkeleton() {
  return (
    <div className="space-y-4 p-4 sm:p-5">
      <Skeleton className="aspect-[16/10] w-full" />
      <div className={statsRow}>
        {[0, 1, 2].map((i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-6 w-20" />
          </div>
        ))}
      </div>
      <Skeleton className="h-3 w-3/4" />
    </div>
  )
}

const statsRow = 'grid h-14 grid-cols-3 gap-3 sm:gap-4'

const fmt = (n: number) => n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function ForecastPanel({ run, onRetry }: { run: RunDetail; onRetry: () => void }) {
  const stage = getStage(run, 'forecast')
  const fc = run.forecast
  const status: RegionStatus = fc
    ? 'ready'
    : stage.status === 'failed'
      ? 'error'
      : stage.status === 'unavailable' || stage.status === 'skipped'
        ? 'empty'
        : stage.status === 'done' || run.status === 'failed' || run.status === 'interrupted'
          ? 'error'
          : 'loading'
  const move = fc?.expected_move_pct ?? 0

  return (
    <Card className="h-full">
      <CardHeader
        title="Price forecast"
        subtitle={fc ? `${fc.model} · ${fc.sample_count} sample paths · next ${fc.horizon} sessions` : 'Kronos model · next 5 sessions'}
      />
      <AsyncRegion
        label="price forecast"
        status={status}
        minHeightClass="min-h-96"
        timeoutMs={5 * 60_000}
        skeleton={<ChartSkeleton />}
        empty={
          <EmptyState
            tone={stage.status === 'unavailable' ? 'warning' : 'neutral'}
            title={stage.status === 'skipped' ? 'Not part of this run' : 'No forecast for this run'}
            description={stage.error ?? undefined}
          />
        }
        errorMessage={stageError(stage, run)}
        onRetry={onRetry}
      >
        {fc && (
          <div className="space-y-4 p-4 sm:p-5">
            <div className="aspect-[16/10] w-full overflow-hidden rounded-lg">
              <Suspense fallback={<Skeleton className="h-full w-full" />}>
                <ForecastChart forecast={fc} analysisDate={run.analysis_date} />
              </Suspense>
            </div>
            <div className={statsRow}>
              <Stat label="Last close" value={<span className="text-sm sm:text-lg">{fmt(fc.last_close)}</span>} />
              <Stat
                label="Expected move"
                tone={Math.abs(move) < 0.5 ? 'neutral' : move > 0 ? 'positive' : 'negative'}
                value={<span className="text-sm sm:text-lg">{`${move > 0 ? '+' : move < 0 ? '−' : '±'}${Math.abs(move).toFixed(1)}%`}</span>}
              />
              <Stat
                label="Range p10–p90"
                value={<span className="block text-xs leading-tight sm:text-lg">{`${fmt(fc.range_low)}–${fmt(fc.range_high)}`}</span>}
              />
            </div>
            <p className="h-3 truncate text-xs leading-3 text-muted" title="A probabilistic input, not a price target.">
              Band: 80% of sample paths · dashed: median path
            </p>
          </div>
        )}
      </AsyncRegion>
    </Card>
  )
}
