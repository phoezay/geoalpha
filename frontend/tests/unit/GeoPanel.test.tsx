import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { GeoPanel } from '../../src/features/run-report/GeoPanel'
import type { GeoSummary, RunDetail, StageKey } from '../../src/lib/api'

const keys: StageKey[] = ['geo', 'forecast', 'market', 'sentiment', 'news', 'fundamentals', 'research_debate', 'trader', 'risk_debate', 'decision']

function run(geoStatus: RunDetail['stages'][number]['status'], geo: GeoSummary | null = null, error: string | null = null): RunDetail {
  return {
    id: 'r1', ticker: 'XOM', requested_date: '2026-10-30', analysis_date: '2026-10-30', status: 'running',
    rating: null, created_at: '2026-11-02T10:00:00Z', finished_at: null, retry_of: null,
    stages: keys.map((key, order) => ({
      key, order, label: key, critical: true, attempts: 1, report_md: null, payload: null,
      started_at: null, finished_at: null,
      status: key === 'geo' ? geoStatus : 'pending', error: key === 'geo' ? error : null,
    })),
    settings: {}, llm_provider: 'x', deep_model: 'd', quick_model: 'q', missing_inputs: [], error: null,
    geo, forecast: null, decision: null, last_event_seq: 0,
  }
}

const material: GeoSummary = {
  materiality: 'material',
  exposure: { countries: [{ iso2: 'SA', weight: 0.15, reason: 'Gulf' }], commodities: ['crude_oil'], chokepoints: ['strait_of_hormuz'] },
  signals: [
    {
      id: 'r1:1', rank: 1, region: 'YE', category: 'supply_route', severity: 4, impact_direction: 'positive',
      headline: 'Commercial vessel targeted in southern Red Sea', rationale: 'Red Sea routing raises tanker rates.',
      valid_at: '2026-10-29T16:00:00Z', source_label: 'WorldMonitor (demo fixture) · get_conflict_events',
      source_url: 'https://www.worldmonitor.app',
    },
  ],
}

describe('GeoPanel (T070)', () => {
  it('loading: five skeleton rows', () => {
    const { container } = render(<GeoPanel run={run('running')} onRetry={() => {}} />)
    expect(screen.getByText('Loading geopolitical signals…')).toBeInTheDocument()
    expect(container.querySelectorAll('li').length).toBe(5)
  })

  it('immaterial: explains no material exposure for the date', () => {
    render(<GeoPanel run={run('done', { materiality: 'immaterial', signals: [] })} onRetry={() => {}} />)
    expect(screen.getByText(/No material geopolitical exposure detected for/)).toBeInTheDocument()
  })

  it('unavailable: amber note with the reason, never current data', () => {
    render(
      <GeoPanel
        run={run('unavailable', { materiality: 'unavailable', unavailable_reason: 'No snapshot recorded for 2024-06-14.', signals: [] })}
        onRetry={() => {}}
      />,
    )
    expect(screen.getByText('Geopolitical data unavailable for this date')).toBeInTheDocument()
    expect(screen.getByText('No snapshot recorded for 2024-06-14.')).toBeInTheDocument()
  })

  it('error: Retry', async () => {
    const onRetry = vi.fn()
    render(<GeoPanel run={run('failed', null, 'WorldMonitor rejected the API key.')} onRetry={onRetry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('WorldMonitor rejected the API key.')
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalled()
  })

  it('ready: severity, category, text impact label, safe source link, expandable rationale', async () => {
    render(<GeoPanel run={run('done', material)} onRetry={() => {}} />)
    const row = document.getElementById('signal-r1:1')!
    const r = within(row)
    expect(r.getByText('Severity 4 of 5')).toBeInTheDocument()
    expect(r.getByText('Supply route')).toBeInTheDocument()
    expect(r.getByText('Tailwind')).toBeInTheDocument()
    const link = r.getByRole('link', { name: /WorldMonitor/ })
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveAttribute('target', '_blank')
    expect(r.queryByText('Red Sea routing raises tanker rates.')).toBeNull()
    await userEvent.click(r.getByRole('button', { name: 'Why it matters' }))
    expect(r.getByText('Red Sea routing raises tanker rates.')).toBeInTheDocument()
    expect(r.getByRole('button', { name: 'Hide why' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Strait of hormuz')).toBeInTheDocument()
  })
})
