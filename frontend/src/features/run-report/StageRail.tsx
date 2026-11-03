import { useEffect, useRef, useState } from 'react'
import { cn } from '../../components/ui'
import type { RunDetail, Stage } from '../../lib/api'
import { duration } from '../../lib/format'

const statusText: Record<Stage['status'], string> = {
  pending: 'waiting',
  running: 'in progress',
  done: 'done',
  failed: 'failed',
  unavailable: 'unavailable',
  skipped: 'not part of this run',
}

function Icon({ status }: { status: Stage['status'] }) {
  switch (status) {
    case 'done':
      return (
        <svg aria-hidden="true" viewBox="0 0 16 16" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="m3.5 8.5 3 3 6-7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    case 'failed':
      return <span aria-hidden="true" className="text-xs font-bold">!</span>
    case 'running':
      return <span aria-hidden="true" className="size-2 animate-pulse rounded-full bg-current motion-reduce:animate-none" />
    case 'unavailable':
      return <span aria-hidden="true" className="text-xs font-bold">–</span>
    default:
      return <span aria-hidden="true" className="size-1.5 rounded-full bg-current opacity-60" />
  }
}

const chipTone: Record<Stage['status'], string> = {
  pending: 'border-border text-muted',
  running: 'border-accent/40 bg-accent-soft text-accent',
  done: 'border-border bg-surface text-fg',
  failed: 'border-negative/40 bg-negative-soft text-negative',
  unavailable: 'border-warning/40 bg-warning-soft text-warning',
  skipped: 'border-dashed border-border text-muted',
}

const iconTone: Record<Stage['status'], string> = {
  pending: 'bg-surface-2',
  running: 'bg-surface',
  done: 'bg-positive-soft text-positive',
  failed: 'bg-surface',
  unavailable: 'bg-surface',
  skipped: 'bg-surface-2',
}

export function StageRail({ run }: { run: RunDetail }) {
  const done = run.stages.filter((s) => ['done', 'skipped', 'unavailable'].includes(s.status)).length
  const announcement = useStageAnnouncement(run)

  return (
    <nav aria-label="Analysis progress" className="min-h-14">
      <div className="mb-2 flex items-center justify-between text-xs text-muted">
        <span>Progress</span>
        <span>
          {done} of {run.stages.length} steps
        </span>
      </div>
      <ol className="relative -mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0 lg:grid lg:grid-cols-10 lg:overflow-visible">
        {run.stages.map((s) => (
          <li key={s.key} className="shrink-0 lg:min-w-0">
            <div
              title={`${s.label}: ${statusText[s.status]}${s.error ? ` (${s.error})` : ''}`}
              className={cn(
                'flex h-9 items-center gap-2 rounded-lg border px-2.5 text-xs font-medium transition-colors lg:px-2',
                chipTone[s.status],
              )}
            >
              <span className={cn('grid size-5 shrink-0 place-items-center rounded-full', iconTone[s.status])}>
                <Icon status={s.status} />
              </span>
              <span className="truncate">{s.label}</span>
              <span className="sr-only">: {statusText[s.status]}</span>
              {s.status === 'done' && duration(s.started_at, s.finished_at) && (
                <span className="ml-auto hidden text-[10px] font-normal text-muted xl:inline">
                  {duration(s.started_at, s.finished_at)}
                </span>
              )}
            </div>
          </li>
        ))}
      </ol>
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
    </nav>
  )
}

/** Announces stage transitions to screen readers without re-reading the whole rail. */
function useStageAnnouncement(run: RunDetail): string {
  const prev = useRef<Record<string, string>>({})
  const [text, setText] = useState('')
  useEffect(() => {
    const changed = run.stages.filter(
      (s) => prev.current[s.key] !== undefined && prev.current[s.key] !== s.status,
    )
    prev.current = Object.fromEntries(run.stages.map((s) => [s.key, s.status]))
    if (changed.length) setText(changed.map((s) => `${s.label} ${statusText[s.status]}`).join('. '))
  }, [run.stages])
  return text
}
