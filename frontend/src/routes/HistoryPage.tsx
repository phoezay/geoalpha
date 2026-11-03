import { useInfiniteQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { Button, Card, EmptyState } from '../components/ui'
import { AsyncRegion } from '../components/ui/AsyncRegion'
import { RunListHeader, RunRow, RunRowSkeleton } from '../features/history/RunList'
import { api } from '../lib/api'

const PAGE = 25

export function HistoryPage() {
  const navigate = useNavigate()
  const runs = useInfiniteQuery({
    queryKey: ['runs', 'history'],
    queryFn: ({ pageParam }) => api.listRuns(PAGE, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  })
  const items = runs.data?.pages.flatMap((p) => p.items) ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">History</h1>
        <p className="mt-1 text-muted">Every analysis you have run, newest first. Open one to see its full report.</p>
      </div>
      <Card>
        <RunListHeader />
        <AsyncRegion
          label="run history"
          status={runs.isPending ? 'loading' : runs.isError ? 'error' : items.length ? 'ready' : 'empty'}
          minHeightClass="min-h-96"
          timeoutMs={15_000}
          skeleton={
            <ul className="divide-y divide-border">
              {Array.from({ length: 8 }, (_, i) => (
                <RunRowSkeleton key={i} />
              ))}
            </ul>
          }
          empty={
            <EmptyState
              title="No runs yet"
              description="Analyses you start will appear here."
              action={
                <Button variant="primary" onClick={() => navigate('/')}>
                  Start an analysis
                </Button>
              }
            />
          }
          errorMessage={runs.error?.message}
          onRetry={() => void runs.refetch()}
        >
          <ul className="divide-y divide-border">
            {items.map((r) => (
              <RunRow key={r.id} run={r} />
            ))}
            {runs.isFetchingNextPage &&
              Array.from({ length: 3 }, (_, i) => <RunRowSkeleton key={`more-${i}`} />)}
          </ul>
          {runs.hasNextPage && (
            <div className="border-t border-border p-3 text-center">
              <Button size="sm" onClick={() => void runs.fetchNextPage()} disabled={runs.isFetchingNextPage}>
                Load more
              </Button>
            </div>
          )}
        </AsyncRegion>
      </Card>
    </div>
  )
}
