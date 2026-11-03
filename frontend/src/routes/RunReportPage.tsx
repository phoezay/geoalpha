import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { Button, Card, ErrorState } from '../components/ui'
import { Skeleton, SkeletonText } from '../components/ui/Skeleton'
import { AnalystTabs } from '../features/run-report/AnalystTabs'
import { DebatePanel } from '../features/run-report/DebatePanel'
import { DecisionCard } from '../features/run-report/DecisionCard'
import { ExportMenu } from '../features/run-report/ExportMenu'
import { ForecastPanel } from '../features/run-report/ForecastPanel'
import { GeoPanel } from '../features/run-report/GeoPanel'
import { RunHeader } from '../features/run-report/RunHeader'
import { useRetryRun } from '../features/run-report/stage-utils'
import { StageRail } from '../features/run-report/StageRail'
import { TraderRiskPanel } from '../features/run-report/TraderRiskPanel'
import { api, ApiError, TERMINAL_RUN } from '../lib/api'
import { runKey, useRunStream } from '../lib/runStream'

export function RunReportPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const run = useQuery({ queryKey: runKey(id), queryFn: () => api.getRun(id) })
  const live = !!run.data && !TERMINAL_RUN.has(run.data.status)
  useRunStream(id, live)
  const retry = useRetryRun(id)

  if (run.isError) {
    const notFound = run.error instanceof ApiError && run.error.status === 404
    return (
      <Card className="min-h-96">
        <ErrorState
          title={notFound ? 'Run not found' : 'Could not load this run'}
          message={notFound ? 'It may have been removed, or the link is wrong.' : run.error.message}
          onRetry={notFound ? undefined : () => void run.refetch()}
        />
      </Card>
    )
  }
  if (!run.data) return <ReportSkeleton />

  const r = run.data
  const onRetry = () => {
    if (r.status === 'failed' || r.status === 'interrupted') retry.mutate('resume')
    else void run.refetch()
  }
  const onCite = (signalId: string) => {
    const el = document.getElementById(`signal-${signalId}`)
    if (!el) return
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' })
    el.focus({ preventScroll: true })
    el.animate?.([{ boxShadow: '0 0 0 3px var(--ga-accent)' }, { boxShadow: '0 0 0 0 transparent' }], {
      duration: reduce ? 1 : 1400,
    })
  }

  return (
    <div className="space-y-6">
      <RunHeader
        run={r}
        actions={
          <div className="flex items-center gap-2">
            {(r.status === 'failed' || r.status === 'interrupted') && (
              <Button variant="primary" size="sm" loading={retry.isPending} onClick={() => retry.mutate('resume')}>
                Resume run
              </Button>
            )}
            {r.status === 'completed' && r.missing_inputs.length > 0 && (
              <Button size="sm" loading={retry.isPending} onClick={() => retry.mutate('fresh', { onSuccess: (n) => navigate(`/runs/${n.id}`) })}>
                Re-run with fresh inputs
              </Button>
            )}
            <ExportMenu run={r} />
          </div>
        }
      />
      {retry.isError && (
        <p role="alert" className="text-sm text-negative">
          {retry.error.message}
        </p>
      )}
      <StageRail run={r} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-12">
          <DecisionCard run={r} onRetry={onRetry} onCite={onCite} />
        </div>
        <div className="lg:col-span-7">
          <GeoPanel run={r} onRetry={onRetry} />
        </div>
        <div className="lg:col-span-5">
          <ForecastPanel run={r} onRetry={onRetry} />
        </div>
        <div className="lg:col-span-12">
          <AnalystTabs run={r} onRetry={onRetry} />
        </div>
        <div className="lg:col-span-6">
          <DebatePanel run={r} onRetry={onRetry} />
        </div>
        <div className="lg:col-span-6">
          <TraderRiskPanel run={r} onRetry={onRetry} />
        </div>
      </div>
    </div>
  )
}

function ReportSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true">
      <span role="status" className="sr-only">
        Loading run…
      </span>
      <div className="min-h-20 space-y-2">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-4 w-72" />
        <Skeleton className="h-3 w-56" />
      </div>
      <div className="min-h-14 space-y-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-9 w-full" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <Card className="min-h-48 p-6 lg:col-span-12">
          <SkeletonText lines={4} />
        </Card>
        <Card className="min-h-96 p-6 lg:col-span-7">
          <SkeletonText lines={8} />
        </Card>
        <Card className="min-h-96 p-6 lg:col-span-5">
          <Skeleton className="aspect-[16/10] w-full" />
        </Card>
      </div>
    </div>
  )
}
