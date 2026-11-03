import type { components } from './api-types'

type S = components['schemas']
export type Health = S['Health']
export type TickerValidation = S['TickerValidation']
export type RunCreate = S['RunCreate']
export type RunDetail = S['RunDetail']
export type RunSummary = S['RunSummary']
export type RunPage = S['RunPage']
export type Stage = S['Stage']
export type StageKey = S['StageKey']
export type StageStatus = S['StageStatus']
export type RunStatus = S['RunStatus']
export type Decision = S['Decision']
export type GeoSummary = S['GeoSummary']
export type GeoSignal = S['GeoSignal']
export type PriceForecast = S['PriceForecast']
export type Rating = Decision['rating']

export class ApiError extends Error {
  readonly status: number
  readonly detail?: string
  readonly fieldErrors: Record<string, string>

  constructor(status: number, title: string, detail?: string, fieldErrors?: Record<string, string>) {
    super(detail || title)
    this.status = status
    this.detail = detail
    this.fieldErrors = fieldErrors ?? {}
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response
  try {
    resp = await fetch(path, {
      ...init,
      headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}) },
    })
  } catch {
    throw new ApiError(0, 'Network error', 'Could not reach the GeoAlpha server. Is it running?')
  }
  if (!resp.ok) {
    let body: { title?: string; detail?: string; field_errors?: Record<string, string> } = {}
    try {
      body = await resp.json()
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(resp.status, body.title ?? resp.statusText, body.detail, body.field_errors)
  }
  return (await resp.json()) as T
}

export const api = {
  health: () => request<Health>('/api/health'),
  validateTicker: (ticker: string) =>
    request<TickerValidation>(`/api/tickers/validate?ticker=${encodeURIComponent(ticker)}`),
  createRun: (body: RunCreate) =>
    request<RunDetail>('/api/runs', { method: 'POST', body: JSON.stringify(body) }),
  listRuns: (limit = 25, cursor?: string | null) =>
    request<RunPage>(`/api/runs?limit=${limit}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`),
  getRun: (id: string) => request<RunDetail>(`/api/runs/${encodeURIComponent(id)}`),
  retryRun: (id: string, mode: 'resume' | 'fresh' = 'resume') =>
    request<RunDetail>(`/api/runs/${encodeURIComponent(id)}/retry`, {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),
  exportUrl: (id: string, format: 'md' | 'html') =>
    `/api/runs/${encodeURIComponent(id)}/export?format=${format}`,
}

export const TICKER_RE = /^[A-Za-z][A-Za-z0-9.-]{0,9}$/
export const TERMINAL_RUN: ReadonlySet<RunStatus> = new Set(['completed', 'failed', 'interrupted'])
