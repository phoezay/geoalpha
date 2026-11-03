import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Card, CardHeader, cn, EmptyState, focusRing } from '../../components/ui'
import { AsyncRegion } from '../../components/ui/AsyncRegion'
import { api } from '../../lib/api'
import { RunRow, RunRowSkeleton } from './RunList'

export function RecentRuns() {
  const runs = useQuery({ queryKey: ['runs', 'recent'], queryFn: () => api.listRuns(5) })
  const items = runs.data?.items ?? []
  return (
    <Card>
      <CardHeader
        title="Recent analyses"
        action={
          <Link to="/history" className={cn('rounded-md text-xs font-medium text-accent hover:underline', focusRing)}>
            View all
          </Link>
        }
      />
      <AsyncRegion
        label="recent analyses"
        status={runs.isPending ? 'loading' : runs.isError ? 'error' : items.length ? 'ready' : 'empty'}
        minHeightClass="min-h-60"
        timeoutMs={15_000}
        skeleton={
          <ul className="divide-y divide-border">
            {Array.from({ length: 5 }, (_, i) => (
              <RunRowSkeleton key={i} />
            ))}
          </ul>
        }
        empty={<EmptyState title="No analyses yet" description="Start your first above." />}
        errorMessage={runs.error?.message}
        onRetry={() => void runs.refetch()}
      >
        <ul className="divide-y divide-border">
          {items.map((r) => (
            <RunRow key={r.id} run={r} />
          ))}
        </ul>
      </AsyncRegion>
    </Card>
  )
}
