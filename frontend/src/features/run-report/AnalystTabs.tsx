import { Card, CardHeader, EmptyState } from '../../components/ui'
import { AsyncRegion } from '../../components/ui/AsyncRegion'
import { SkeletonText } from '../../components/ui/Skeleton'
import { Tabs } from '../../components/ui/Tabs'
import type { RunDetail, StageKey } from '../../lib/api'
import { Markdown } from './Markdown'
import { getStage, REPORT_TIMEOUT_MS, stageError, stageRegionStatus } from './stage-utils'

const analysts: { key: StageKey; label: string }[] = [
  { key: 'market', label: 'Market' },
  { key: 'sentiment', label: 'Sentiment' },
  { key: 'news', label: 'News' },
  { key: 'fundamentals', label: 'Fundamentals' },
]

const dot: Record<string, string> = {
  done: 'bg-positive',
  running: 'bg-accent animate-pulse motion-reduce:animate-none',
  failed: 'bg-negative',
}

export function AnalystTabs({ run, onRetry }: { run: RunDetail; onRetry: () => void }) {
  return (
    <Card>
      <CardHeader title="Analyst reports" subtitle="What each specialist found before the debate" />
      <Tabs
        label="Analyst reports"
        items={analysts.map(({ key, label }) => {
          const stage = getStage(run, key)
          return {
            key,
            label,
            badge: dot[stage.status] ? (
              <span aria-hidden="true" className={`size-1.5 rounded-full ${dot[stage.status]}`} />
            ) : undefined,
            content: (
              <AsyncRegion
                label={`${label.toLowerCase()} report`}
                status={stageRegionStatus(stage, run.status)}
                minHeightClass="min-h-64"
                timeoutMs={REPORT_TIMEOUT_MS}
                skeleton={<SkeletonText lines={6} className="p-5" />}
                empty={<EmptyState title="This analyst was not part of the run" />}
                errorMessage={stageError(stage, run)}
                onRetry={onRetry}
              >
                <div className="p-4 sm:p-5">
                  <Markdown>{stage.report_md ?? '_No report text was produced._'}</Markdown>
                </div>
              </AsyncRegion>
            ),
          }
        })}
      />
    </Card>
  )
}
