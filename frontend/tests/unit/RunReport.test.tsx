import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest'
import type { RunDetail, StageKey } from '../../src/lib/api'
import { RunReportPage } from '../../src/routes/RunReportPage'

/* ---------------------------------------------------------------- fakes */

class FakeEventSource {
  url: string
  static last: FakeEventSource | null = null
  listeners = new Map<string, ((e: MessageEvent) => void)[]>()
  closed = false
  constructor(url: string) {
    this.url = url
    FakeEventSource.last = this
  }
  addEventListener(type: string, fn: (e: MessageEvent) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), fn])
  }
  close() {
    this.closed = true
  }
  emit(seq: number, type: string, data: Record<string, unknown>) {
    const ev = { seq, run_id: 'r1', type, at: new Date().toISOString(), data }
    for (const fn of this.listeners.get(type) ?? []) fn(new MessageEvent(type, { data: JSON.stringify(ev) }))
  }
}

const keys: StageKey[] = [
  'geo', 'forecast', 'market', 'sentiment', 'news', 'fundamentals',
  'research_debate', 'trader', 'risk_debate', 'decision',
]

function makeRun(over: Partial<RunDetail> = {}): RunDetail {
  return {
    id: 'r1',
    ticker: 'XOM',
    requested_date: '2026-10-30',
    analysis_date: '2026-10-30',
    status: 'running',
    rating: null,
    created_at: '2026-11-02T10:00:00Z',
    finished_at: null,
    retry_of: null,
    stages: keys.map((key, order) => ({
      key, order, label: key, critical: !['geo', 'forecast'].includes(key),
      status: 'pending', attempts: 0, report_md: null, payload: null, error: null,
      started_at: null, finished_at: null,
    })),
    settings: {},
    llm_provider: 'anthropic',
    deep_model: 'claude-opus-5-5',
    quick_model: 'claude-sonnet-5',
    missing_inputs: [],
    error: null,
    geo: null,
    forecast: null,
    decision: null,
    last_event_seq: 0,
    ...over,
  }
}

let current: RunDetail = makeRun()
const server = setupServer(http.get('/api/runs/:id', () => HttpResponse.json(current)))

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterAll(() => server.close())
afterEach(() => server.resetHandlers())
beforeEach(() => {
  ;(globalThis as unknown as { EventSource: unknown }).EventSource = FakeEventSource
  FakeEventSource.last = null
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter([{ path: '/runs/:id', element: <RunReportPage /> }], {
    initialEntries: ['/runs/r1'],
  })
  return render(
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

const region = (name: string) => screen.getByRole('heading', { name }).closest('section')!

/* ---------------------------------------------------------------- tests */

describe('Run report (T037)', () => {
  it('all stages pending: decision and report regions show skeletons, no spinners', async () => {
    current = makeRun()
    renderPage()
    expect(await screen.findByRole('heading', { name: 'XOM' })).toBeInTheDocument()
    expect(screen.getByText('Loading final decision…')).toBeInTheDocument()
    expect(screen.getByText('Loading debate…')).toBeInTheDocument()
    expect(screen.getByText('Loading market report…')).toBeInTheDocument()
    expect(screen.queryAllByRole('progressbar')).toHaveLength(0)
    expect(screen.getByText('Research output, not financial advice.')).toBeInTheDocument()
  })

  it('stage.completed for market swaps only the Market tab content', async () => {
    current = makeRun()
    renderPage()
    await screen.findByRole('heading', { name: 'XOM' })
    act(() => FakeEventSource.last!.emit(1, 'stage.completed', { stage: 'market', report_md: '## Market view\n\nTrend up.', payload: null }))
    expect(await screen.findByRole('heading', { name: 'Market view' })).toBeInTheDocument()
    expect(screen.getByText('Loading debate…')).toBeInTheDocument()
    expect(screen.getByText('Loading final decision…')).toBeInTheDocument()
  })

  it('stage.failed shows an error with Retry in that region', async () => {
    current = makeRun()
    renderPage()
    await screen.findByRole('heading', { name: 'XOM' })
    act(() =>
      FakeEventSource.last!.emit(1, 'stage.failed', { stage: 'research_debate', message: 'LLM rate limited', retryable: true }),
    )
    const debate = region('Bull vs Bear debate')
    expect(await within(debate).findByRole('alert')).toHaveTextContent('LLM rate limited')
    expect(within(debate).getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it('completed run: rating shown with its text label, no stream opened', async () => {
    current = makeRun({
      status: 'completed',
      rating: 'Overweight',
      finished_at: '2026-11-02T10:05:00Z',
      decision: {
        rating: 'Overweight', confidence: 'medium', summary: 'Staged overweight position.',
        rationale_md: 'x', geo_statement: 'unavailable', cited_signal_ids: [],
        forecast_alignment: 'unavailable', missing_inputs: [], disclaimer: 'Research output, not financial advice.',
      },
    })
    current.stages = current.stages.map((s) => ({ ...s, status: 'done' }))
    renderPage()
    expect(await screen.findByText('Overweight')).toBeInTheDocument()
    expect(screen.getByText('Medium confidence')).toBeInTheDocument()
    expect(screen.getByText('Staged overweight position.')).toBeInTheDocument()
    expect(FakeEventSource.last).toBeNull()
  })

  it('run.finished with failure turns the decision skeleton into a resumable error', async () => {
    current = makeRun()
    renderPage()
    await screen.findByRole('heading', { name: 'XOM' })
    // What the server returns when the client refetches after run.finished.
    current = makeRun({ status: 'failed', error: 'Trader failed: Timed out', last_event_seq: 2 })
    act(() => {
      FakeEventSource.last!.emit(1, 'stage.failed', { stage: 'trader', message: 'Timed out', retryable: true })
      FakeEventSource.last!.emit(2, 'run.finished', { status: 'failed', error: 'Trader failed: Timed out' })
    })
    expect(await screen.findByText('Trader failed: Timed out')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Resume run' }).length).toBeGreaterThan(0)
  })
})
