import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { delay, http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import type { RunSummary } from '../../src/lib/api'
import { HistoryPage } from '../../src/routes/HistoryPage'

const server = setupServer()
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterAll(() => server.close())
afterEach(() => server.resetHandlers())

const summary = (i: number): RunSummary => ({
  id: `r${i}`, ticker: i % 2 ? 'XOM' : 'KO', requested_date: '2026-10-30', analysis_date: '2026-10-30',
  status: 'completed', rating: i % 2 ? 'Overweight' : 'Hold', created_at: '2026-11-02T10:00:00Z',
  finished_at: '2026-11-02T10:05:00Z', retry_of: null,
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/history"]}>
        <Routes>
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/" element={<p>New analysis page</p>} />
          <Route path="/runs/:id" element={<p>Report page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('History (T085)', () => {
  it('loading: 8 skeleton rows', async () => {
    server.use(http.get('/api/runs', async () => { await delay('infinite'); return HttpResponse.json({}) }))
    const { container } = renderPage()
    expect(await screen.findByText('Loading run history…')).toBeInTheDocument()
    expect(container.querySelectorAll('li[aria-hidden="true"]').length).toBe(8)
  })

  it('empty: invites starting an analysis', async () => {
    server.use(http.get('/api/runs', () => HttpResponse.json({ items: [], next_cursor: null })))
    renderPage()
    expect(await screen.findByText('No runs yet')).toBeInTheDocument()
    const btn = screen.getByRole('button', { name: 'Start an analysis' })
    await userEvent.click(btn)
    expect(await screen.findByText('New analysis page')).toBeInTheDocument()
  })

  it('error: Retry', async () => {
    server.use(http.get('/api/runs', () => HttpResponse.json({ title: 'Boom', status: 500 }, { status: 500 })))
    renderPage()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it('ready: linked rows with rating labels; Load more appends the next page', async () => {
    server.use(
      http.get('/api/runs', ({ request }) => {
        const cursor = new URL(request.url).searchParams.get('cursor')
        return cursor
          ? HttpResponse.json({ items: [summary(3)], next_cursor: null })
          : HttpResponse.json({ items: [summary(1), summary(2)], next_cursor: 'r2' })
      }),
    )
    renderPage()
    const links = await screen.findAllByRole('link')
    expect(links[0]).toHaveAttribute('href', '/runs/r1')
    expect(screen.getByText('Overweight')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Load more' }))
    await waitFor(() => expect(screen.getAllByRole('link')).toHaveLength(3))
    expect(screen.queryByRole('button', { name: 'Load more' })).toBeNull()
  })
})
