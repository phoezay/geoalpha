import { Badge, Card, cn, ErrorState, focusRing, Stat } from '../../components/ui'
import { AsyncRegion, type RegionStatus } from '../../components/ui/AsyncRegion'
import { Skeleton, SkeletonText } from '../../components/ui/Skeleton'
import type { Decision, GeoSignal, RunDetail } from '../../lib/api'
import { ratingTone } from '../../lib/format'
import { getStage, REPORT_TIMEOUT_MS, stageError } from './stage-utils'

const confidenceTone = { low: 'warning', medium: 'neutral', high: 'positive' } as const

const alignmentText: Record<Decision['forecast_alignment'], string> = {
  supports: 'The price model supports this rating.',
  contradicts: 'The price model points the other way. Treat with caution.',
  neutral: 'The price model expects little movement.',
  unavailable: 'No price-model forecast was available.',
}

const inputLabel: Record<string, string> = { geo: 'geopolitical analysis', forecast: 'price forecast' }

function DecisionSkeleton() {
  return (
    <div className="grid gap-6 p-5 sm:grid-cols-[14rem_1fr] sm:p-6">
      <div className="space-y-3">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-9 w-36" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-5 w-20" />
        </div>
      </div>
      <SkeletonText lines={3} className="pt-1" />
    </div>
  )
}

export function DecisionCard({
  run,
  onRetry,
  onCite,
}: {
  run: RunDetail
  onRetry: () => void
  onCite?: (signalId: string) => void
}) {
  const stage = getStage(run, 'decision')
  const d = run.decision
  const status: RegionStatus = d
    ? 'ready'
    : run.status === 'failed' || run.status === 'interrupted' || stage.status === 'failed'
      ? 'error'
      : 'loading'

  return (
    <Card aria-labelledby="decision-title" className="overflow-hidden">
      <h2 id="decision-title" className="sr-only">
        Final decision
      </h2>
      <AsyncRegion
        label="final decision"
        status={status}
        minHeightClass="min-h-48"
        timeoutMs={REPORT_TIMEOUT_MS}
        skeleton={<DecisionSkeleton />}
        onRetry={onRetry}
        error={
          <ErrorState
            title="No decision yet"
            message={run.error ?? stageError(stage, run)}
            onRetry={onRetry}
            retryLabel="Resume run"
          />
        }
      >
        {d && <DecisionBody decision={d} onCite={onCite} signals={run.geo?.signals ?? []} />}
      </AsyncRegion>
    </Card>
  )
}

function DecisionBody({
  decision: d,
  onCite,
  signals,
}: {
  decision: Decision
  onCite?: (id: string) => void
  signals: GeoSignal[]
}) {
  const byId = new Map(signals.map((s) => [s.id, s]))
  const tone = ratingTone(d.rating)
  return (
    <div className="grid gap-6 p-5 sm:grid-cols-[14rem_1fr] sm:p-6">
      <div className="space-y-3">
        <Stat label="Committee rating" value={d.rating} tone={tone} />
        <div className="flex flex-wrap gap-2">
          <Badge tone={confidenceTone[d.confidence]}>
            {d.confidence[0]!.toUpperCase() + d.confidence.slice(1)} confidence
          </Badge>
        </div>
      </div>
      <div className="min-w-0 space-y-3">
        <p className="text-[15px] leading-relaxed text-fg">{d.summary}</p>
        <ul className="space-y-1.5 text-xs text-muted">
          <li className="flex gap-2">
            <span aria-hidden="true">◇</span>
            <span>{alignmentText[d.forecast_alignment]}</span>
          </li>
          <li className="flex flex-wrap items-center gap-2">
            <span aria-hidden="true">◇</span>
            {d.geo_statement === 'cites' ? (
              <>
                <span>Geopolitical factors cited:</span>
                {d.cited_signal_ids.map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => onCite?.(id)}
                    className={cn(
                      'rounded-md bg-accent-soft px-1.5 py-0.5 font-mono text-[11px] text-accent hover:underline',
                      focusRing,
                    )}
                  >
                    #{id.split(':').pop()}
                    {byId.get(id) && <span className="font-sans"> {byId.get(id)!.region}</span>}
                    <span className="sr-only"> (go to signal)</span>
                  </button>
                ))}
              </>
            ) : d.geo_statement === 'none_material' ? (
              <span>No material geopolitical factors for this ticker.</span>
            ) : (
              <span>Geopolitical data was unavailable for this run.</span>
            )}
          </li>
        </ul>
        {d.missing_inputs.length > 0 && (
          <p className="rounded-md bg-warning-soft px-3 py-2 text-xs text-warning">
            Missing inputs: {d.missing_inputs.map((k) => inputLabel[k] ?? k).join(', ')}. The decision
            was made without them, so confidence is capped at medium.
          </p>
        )}
      </div>
    </div>
  )
}
