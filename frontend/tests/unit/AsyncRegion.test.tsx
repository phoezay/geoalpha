import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AsyncRegion } from '../../src/components/ui/AsyncRegion'
import { Skeleton } from '../../src/components/ui/Skeleton'

const region = (props: Partial<Parameters<typeof AsyncRegion>[0]>) => (
  <AsyncRegion
    label="widget"
    status="loading"
    minHeightClass="min-h-48"
    skeleton={<Skeleton className="h-10" />}
    {...props}
  >
    <p>Loaded content</p>
  </AsyncRegion>
)

describe('AsyncRegion (T028)', () => {
  it('loading: renders the skeleton with aria-busy and an sr-only label, no spinner', () => {
    const { container } = render(region({}))
    const root = container.firstElementChild!
    expect(root).toHaveAttribute('aria-busy', 'true')
    expect(root).toHaveClass('min-h-48')
    expect(screen.getByRole('status')).toHaveTextContent('Loading widget…')
    expect(container.querySelector('[data-skeleton]')).toHaveClass('motion-reduce:animate-none')
    expect(screen.queryByRole('progressbar')).toBeNull()
    expect(screen.queryByText('Loaded content')).toBeNull()
  })

  it('empty: renders the empty node and keeps the min height', () => {
    const { container } = render(region({ status: 'empty', empty: <p>Nothing here</p> }))
    expect(screen.getByText('Nothing here')).toBeInTheDocument()
    expect(container.firstElementChild).toHaveClass('min-h-48')
    expect(container.firstElementChild).not.toHaveAttribute('aria-busy')
  })

  it('error: renders ErrorState whose Retry calls onRetry', async () => {
    const onRetry = vi.fn()
    render(region({ status: 'error', errorMessage: 'Boom', onRetry }))
    expect(screen.getByRole('alert')).toHaveTextContent('Boom')
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('ready: renders children', () => {
    render(region({ status: 'ready' }))
    expect(screen.getByText('Loaded content')).toBeInTheDocument()
  })

  it('a skeleton never stays forever: loading turns into an error after the timeout', () => {
    vi.useFakeTimers()
    try {
      render(region({ timeoutMs: 1000 }))
      expect(screen.getByRole('status')).toBeInTheDocument()
      act(() => vi.advanceTimersByTime(1001))
      expect(screen.getByRole('alert')).toHaveTextContent('Taking longer than expected')
    } finally {
      vi.useRealTimers()
    }
  })
})
