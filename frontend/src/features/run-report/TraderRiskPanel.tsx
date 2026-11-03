import { Card, CardHeader, cn, focusRing } from '../../components/ui'
import { AsyncRegion } from '../../components/ui/AsyncRegion'
import { Skeleton, SkeletonText } from '../../components/ui/Skeleton'
import type { RunDetail } from '../../lib/api'
import { Markdown } from './Markdown'
import { getStage, REPORT_TIMEOUT_MS, stageError, stageRegionStatus } from './stage-utils'

type RiskPayload = { aggressive?: string; conservative?: string; neutral?: string }

const perspectives: { key: keyof RiskPayload; label: string }[] = [
  { key: 'aggressive', label: 'Aggressive' },
  { key: 'conservative', label: 'Conservative' },
  { key: 'neutral', label: 'Neutral' },
]

function BlocksSkeleton() {
  return (
    <div className="space-y-4 p-4 sm:p-5">
      <SkeletonText lines={4} />
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  )
}

export function TraderRiskPanel({ run, onRetry }: { run: RunDetail; onRetry: () => void }) {
  const trader = getStage(run, 'trader')
  const risk = getStage(run, 'risk_debate')
  const traderStatus = stageRegionStatus(trader, run.status)
  const riskStatus = stageRegionStatus(risk, run.status)
  const payload = (risk.payload ?? {}) as RiskPayload

  return (
    <Card>
      <CardHeader title="Trader & risk review" subtitle="Proposed position, then three risk perspectives" />
      <AsyncRegion
        label="trader proposal"
        status={traderStatus}
        minHeightClass="min-h-64"
        timeoutMs={REPORT_TIMEOUT_MS}
        skeleton={<BlocksSkeleton />}
        errorMessage={stageError(trader, run)}
        onRetry={onRetry}
      >
        <div className="space-y-4 p-4 sm:p-5">
          <Markdown>{trader.report_md ?? '_No trader proposal._'}</Markdown>
          <AsyncRegion
            label="risk review"
            status={riskStatus}
            timeoutMs={REPORT_TIMEOUT_MS}
            skeleton={
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            }
            errorMessage={stageError(risk, run)}
            onRetry={onRetry}
          >
            <div className="divide-y divide-border rounded-lg border border-border">
              {perspectives.map(({ key, label }) =>
                payload[key] ? (
                  <details key={key} className="group">
                    <summary
                      className={cn(
                        'flex h-10 cursor-pointer list-none items-center justify-between rounded-lg px-3 text-sm font-medium',
                        focusRing,
                      )}
                    >
                      {label} view
                      <span aria-hidden="true" className="text-muted transition-transform group-open:rotate-90">
                        ›
                      </span>
                    </summary>
                    <div className="px-3 pb-3">
                      <Markdown className="prose-p:my-1">{payload[key]!.trim()}</Markdown>
                    </div>
                  </details>
                ) : null,
              )}
            </div>
          </AsyncRegion>
        </div>
      </AsyncRegion>
    </Card>
  )
}
