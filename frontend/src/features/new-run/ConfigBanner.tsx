import { useQuery } from '@tanstack/react-query'
import { Button } from '../../components/ui'
import { api } from '../../lib/api'

export function useHealth() {
  return useQuery({ queryKey: ['health'], queryFn: api.health, staleTime: 30_000 })
}

/**
 * Shows configuration problems before a run can start (edge case: missing LLM key).
 * No skeleton on purpose: in the common case there is nothing to show, so reserving space
 * would itself cause a layout shift when it collapses (contracts/ui-states.md).
 */
export function ConfigBanner() {
  const health = useHealth()

  if (health.isError) {
    return (
      <div
        role="alert"
        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-negative/30 bg-negative-soft px-4 py-3 text-sm text-negative"
      >
        <span>{health.error.message}</span>
        <Button size="sm" onClick={() => void health.refetch()}>
          Retry
        </Button>
      </div>
    )
  }
  const problems = health.data?.problems ?? []
  if (problems.length === 0) return null

  return (
    <div
      role="alert"
      className="rounded-lg border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning"
    >
      <p className="font-medium">GeoAlpha needs configuration before it can run</p>
      <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs">
        {problems.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    </div>
  )
}
