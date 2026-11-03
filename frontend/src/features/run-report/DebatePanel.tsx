import { Badge, Card, CardHeader, cn } from '../../components/ui'
import { AsyncRegion } from '../../components/ui/AsyncRegion'
import { Skeleton } from '../../components/ui/Skeleton'
import type { RunDetail } from '../../lib/api'
import { Markdown } from './Markdown'
import { getStage, REPORT_TIMEOUT_MS, stageError, stageRegionStatus } from './stage-utils'

type DebatePayload = { bull_history?: string; bear_history?: string; judge?: string }

function DebateSkeleton() {
  return (
    <div className="space-y-3 p-4 sm:p-5">
      {[0, 1, 2].map((i) => (
        <div key={i} className={cn('flex', i % 2 ? 'justify-end' : 'justify-start')}>
          <Skeleton className={cn('h-16 rounded-xl', i === 2 ? 'w-full' : 'w-4/5')} />
        </div>
      ))}
    </div>
  )
}

function Turn({ side, text }: { side: 'bull' | 'bear'; text: string }) {
  const bull = side === 'bull'
  return (
    <div className={cn('flex', bull ? 'justify-start' : 'justify-end')}>
      <div
        className={cn(
          'max-w-[92%] rounded-xl border px-3.5 py-2.5',
          bull ? 'border-positive/25 bg-positive-soft' : 'border-negative/25 bg-negative-soft',
        )}
      >
        <Badge tone={bull ? 'positive' : 'negative'} className="mb-1.5 px-1.5">
          {bull ? 'Bull' : 'Bear'}
        </Badge>
        <Markdown className="prose-p:my-1">{text.trim()}</Markdown>
      </div>
    </div>
  )
}

export function DebatePanel({ run, onRetry }: { run: RunDetail; onRetry: () => void }) {
  const stage = getStage(run, 'research_debate')
  const p = (stage.payload ?? {}) as DebatePayload
  return (
    <Card>
      <CardHeader title="Bull vs Bear debate" subtitle="Researchers argue, then the Research Manager decides" />
      <AsyncRegion
        label="debate"
        status={stageRegionStatus(stage, run.status)}
        minHeightClass="min-h-64"
        timeoutMs={REPORT_TIMEOUT_MS}
        skeleton={<DebateSkeleton />}
        errorMessage={stageError(stage, run)}
        onRetry={onRetry}
      >
        <div className="space-y-3 p-4 sm:p-5">
          {p.bull_history && <Turn side="bull" text={p.bull_history} />}
          {p.bear_history && <Turn side="bear" text={p.bear_history} />}
          {(p.judge || stage.report_md) && (
            <div className="rounded-xl border border-border bg-surface-2 px-3.5 py-2.5">
              <Badge tone="accent" className="mb-1.5 px-1.5">
                Research Manager
              </Badge>
              <Markdown className="prose-p:my-1">{(p.judge || stage.report_md)!}</Markdown>
            </div>
          )}
        </div>
      </AsyncRegion>
    </Card>
  )
}
