import type { ReactNode } from 'react'
import { Badge, Disclaimer } from '../../components/ui'
import type { RunDetail } from '../../lib/api'
import { formatDate, statusLabel, statusTone } from '../../lib/format'

export function RunHeader({ run, actions }: { run: RunDetail; actions?: ReactNode }) {
  const adjusted = run.requested_date !== run.analysis_date
  return (
    <header className="flex min-h-20 flex-wrap items-start justify-between gap-x-6 gap-y-3">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-2xl font-semibold tracking-tight">{run.ticker}</h1>
          <Badge tone={statusTone(run.status)}>
            {(run.status === 'running' || run.status === 'queued') && (
              <span aria-hidden="true" className="size-1.5 animate-pulse rounded-full bg-current motion-reduce:animate-none" />
            )}
            {statusLabel[run.status]}
          </Badge>
        </div>
        <p className="mt-1 text-sm text-muted">
          Analysis date <span className="font-medium text-fg">{formatDate(run.analysis_date)}</span>
          {adjusted && (
            <span className="text-warning"> · adjusted from {formatDate(run.requested_date)} (not a trading day)</span>
          )}
        </p>
        <p className="mt-0.5 flex flex-wrap gap-x-3 text-xs text-muted">
          <span>Provider: {run.llm_provider}</span>
          <span>Models: {run.deep_model} / {run.quick_model}</span>
          {run.retry_of && <span>Re-run of an earlier analysis</span>}
        </p>
      </div>
      <div className="flex flex-col items-start gap-2 sm:items-end">
        {actions}
        <Disclaimer />
      </div>
    </header>
  )
}
