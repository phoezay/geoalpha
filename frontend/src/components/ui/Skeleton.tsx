import { cn } from './index'

/** Placeholder block. Static under reduced motion; hidden from assistive tech
 *  (the surrounding AsyncRegion announces the loading state instead). */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      data-skeleton=""
      className={cn('animate-pulse rounded-md bg-skeleton motion-reduce:animate-none', className)}
    />
  )
}

const widths = ['w-full', 'w-11/12', 'w-4/5', 'w-full', 'w-3/4', 'w-5/6', 'w-2/3']

export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div aria-hidden="true" className={cn('space-y-2.5', className)}>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton
          key={i}
          className={cn('h-3', i === lines - 1 && lines > 1 ? 'w-1/2' : widths[i % widths.length])}
        />
      ))}
    </div>
  )
}
