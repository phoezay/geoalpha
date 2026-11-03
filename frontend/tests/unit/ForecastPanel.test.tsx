import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ForecastPanel } from '../../src/features/run-report/ForecastPanel'
import type { PriceForecast, RunDetail, StageKey } from '../../src/lib/api'

vi.mock('../../src/features/run-report/ForecastChart', () => ({
  ForecastChart: () => <div data-testid="chart" />,
}))

const keys: StageKey[] = ['geo', 'forecast', 'market', 'sentiment', 'news', 'fundamentals', 'research_debate', 'trader', 'risk_debate', 'decision']

function run(forecastStatus: RunDetail['stages'][number]['status'], over: Partial<RunDetail> = {}, error: string | null = null): RunDetail {
  return {
    id: 'r1', ticker: 'XOM', requested_date: '2026-10-30', analysis_date: '2026-10-30', status: 'running',
    rating: null, created_at: '2026-11-02T10:00:00Z', finished_at: null, retry_of: null,
    stages: keys.map((key, order) => ({
      key, order, label: key, critical: true, attempts: 1, report_md: null, payload: null,
      started_at: null, finished_at: null,
      status: key === 'forecast' ? forecastStatus : 'pending',
      error: key === 'forecast' ? error : null,
    })),
    settings: {}, llm_provider: 'x', deep_model: 'd', quick_model: 'q', missing_inputs: [], error: null,
    geo: null, forecast: null, decision: null, last_event_seq: 0, ...over,
  }
}

const fc: PriceForecast = {
  model: 'NeoQuasar/Kronos-small', horizon: 5, sample_count: 30, last_close: 100,
  expected_move_pct: 2.34, range_low: 96.5, range_high: 107.25,
  history: [{ date: '2026-10-30', open: 99, high: 101, low: 98, close: 100, volume: 1 }],
  path: Array.from({ length: 5 }, (_, i) => ({ date: `2026-11-0${i + 2}`, p10: 97, p50: 101, p90: 105 })),
}

describe('ForecastPanel (T057)', () => {
  it('loading: skeleton keeps the chart aspect ratio', () => {
    const { container } = render(<ForecastPanel run={run('running')} onRetry={() => {}} />)
    expect(screen.getByText('Loading price forecast…')).toBeInTheDocument()
    expect(container.querySelector('[data-skeleton].aspect-\\[16\\/10\\]')).not.toBeNull()
  })

  it('unavailable: explains there is not enough history', () => {
    render(<ForecastPanel run={run('unavailable', {}, 'Not enough price history to forecast (56 of 120 trading days).')} onRetry={() => {}} />)
    expect(screen.getByText('No forecast for this run')).toBeInTheDocument()
    expect(screen.getByText(/Not enough price history to forecast/)).toBeInTheDocument()
  })

  it('error: shows Retry', async () => {
    const onRetry = vi.fn()
    render(<ForecastPanel run={run('failed', {}, 'Model download failed')} onRetry={onRetry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Model download failed')
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalled()
  })

  it('ready: renders chart and stats with a signed move', async () => {
    render(<ForecastPanel run={run('done', { forecast: fc })} onRetry={() => {}} />)
    expect(await screen.findByTestId('chart')).toBeInTheDocument()
    expect(screen.getByText('+2.3%')).toBeInTheDocument()
    expect(screen.getByText('100.00')).toBeInTheDocument()
    expect(screen.getByText('96.50–107.25')).toBeInTheDocument()
  })
})
