import { Link } from 'react-router'
import { Badge, cn, focusRing } from '../../components/ui'
import { Skeleton } from '../../components/ui/Skeleton'
import type { RunSummary } from '../../lib/api'
import { formatDate, ratingTone, relativeTime, statusLabel, statusTone } from '../../lib/format'

/** Column template shared by rows and skeleton rows so widths match exactly (no CLS). */
const cols = 'md:grid md:grid-cols-[7rem_1fr_8rem_8rem_8rem] md:items-center md:gap-4'

export function RunListHeader() {
  return (
    <div
      aria-hidden="true"
      className={cn('hidden border-b border-border px-4 py-2 text-xs font-medium text-muted sm:px-5', cols)}
    >
      <span>Ticker</span>
      <span>Analysis date</span>
      <span>Rating</span>
      <span>Status</span>
      <span className="text-right">Finished</span>
    </div>
  )
}

export function RunRow({ run }: { run: RunSummary }) {
  return (
    <li>
      <Link
        to={`/runs/${run.id}`}
        className={cn(
          'flex min-h-12 flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 transition-colors hover:bg-surface-2 sm:px-5 md:py-0',
          cols,
          focusRing,
        )}
      >
        <span className="font-semibold">{run.ticker}</span>
        <span className="text-muted md:text-fg">{formatDate(run.analysis_date)}</span>
        <span className="basis-full md:basis-auto">
          {run.rating ? (
            <Badge tone={ratingTone(run.rating)}>{run.rating}</Badge>
          ) : (
            <span className="text-xs text-muted">No rating</span>
          )}
        </span>
        <span>
          <Badge tone={statusTone(run.status)}>{statusLabel[run.status]}</Badge>
        </span>
        <span className="ml-auto text-xs text-muted md:text-right" title={run.finished_at ?? undefined}>
          {run.finished_at ? relativeTime(run.finished_at) : 'In progress'}
        </span>
      </Link>
    </li>
  )
}

export function RunRowSkeleton() {
  return (
    <li aria-hidden="true" className={cn('flex min-h-12 flex-wrap items-center gap-3 px-4 py-3 sm:px-5 md:py-0', cols)}>
      <Skeleton className="h-4 w-14" />
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-5 w-20" />
      <Skeleton className="h-5 w-20" />
      <Skeleton className="ml-auto h-3 w-16" />
    </li>
  )
}
