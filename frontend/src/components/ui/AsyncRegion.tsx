import { useEffect, useState, type ReactNode } from 'react'
import { cn, EmptyState, ErrorState } from './index'

export type RegionStatus = 'loading' | 'empty' | 'error' | 'ready'

/**
 * Every async region renders through this (Constitution IV, contracts/ui-states.md):
 * - loading: a skeleton inside a container that keeps the ready state's min height (no CLS),
 *   aria-busy plus an sr-only announcement; after `timeoutMs` it becomes an error with Retry.
 * - empty / error / ready: the matching state, same container.
 */
export function AsyncRegion({
  status,
  label,
  skeleton,
  empty,
  error,
  errorMessage,
  onRetry,
  timeoutMs = 30_000,
  minHeightClass,
  className,
  children,
}: {
  status: RegionStatus
  label: string
  skeleton: ReactNode
  empty?: ReactNode
  error?: ReactNode
  errorMessage?: ReactNode
  onRetry?: () => void
  timeoutMs?: number
  minHeightClass?: string
  className?: string
  children?: ReactNode
}) {
  const timedOut = useTimeout(status === 'loading', timeoutMs)
  const effective: RegionStatus = status === 'loading' && timedOut ? 'error' : status

  return (
    <div
      aria-busy={effective === 'loading' || undefined}
      data-region-status={effective}
      className={cn(minHeightClass, className)}
    >
      {effective === 'loading' && (
        <>
          <span role="status" className="sr-only">
            Loading {label}…
          </span>
          {skeleton}
        </>
      )}
      {effective === 'empty' && (empty ?? <EmptyState title={`No ${label} to show`} />)}
      {effective === 'error' &&
        (status === 'loading' ? (
          <ErrorState
            title="Taking longer than expected"
            message={`${label} has not loaded yet.`}
            onRetry={onRetry}
          />
        ) : (
          (error ?? <ErrorState message={errorMessage} onRetry={onRetry} />)
        ))}
      {effective === 'ready' && children}
    </div>
  )
}

function useTimeout(active: boolean, ms: number): boolean {
  const [expired, setExpired] = useState(false)
  useEffect(() => {
    if (!active) {
      setExpired(false)
      return
    }
    const id = window.setTimeout(() => setExpired(true), ms)
    return () => window.clearTimeout(id)
  }, [active, ms])
  return active && expired
}
