import { useQueryClient, type QueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import type { Decision, GeoSummary, PriceForecast, RunDetail, Stage, StageKey } from './api'

export const runKey = (id: string) => ['run', id] as const

type RunEvent = {
  seq: number
  run_id: string
  type: string
  at: string
  data: Record<string, unknown>
}

const EVENT_TYPES = [
  'run.started',
  'stage.started',
  'stage.completed',
  'stage.failed',
  'stage.unavailable',
  'geo.ready',
  'forecast.ready',
  'decision.ready',
  'run.finished',
] as const

function patchStage(run: RunDetail, key: StageKey, patch: Partial<Stage>): RunDetail {
  return { ...run, stages: run.stages.map((s) => (s.key === key ? { ...s, ...patch } : s)) }
}

/** Applies one SSE event (contracts/sse-events.schema.json) to the cached RunDetail. */
export function applyEvent(run: RunDetail, ev: RunEvent): RunDetail {
  const d = ev.data
  const next: RunDetail = { ...run, last_event_seq: Math.max(run.last_event_seq, ev.seq) }
  switch (ev.type) {
    case 'run.started':
      return { ...next, status: 'running', error: null }
    case 'stage.started':
      return patchStage(next, d.stage as StageKey, {
        status: 'running',
        attempts: d.attempt as number,
        error: null,
        started_at: ev.at,
        finished_at: null,
      })
    case 'stage.completed':
      return patchStage(next, d.stage as StageKey, {
        status: (d.status as Stage['status']) ?? 'done',
        report_md: (d.report_md as string | null) ?? null,
        payload: (d.payload as Stage['payload']) ?? null,
        finished_at: ev.at,
      })
    case 'stage.failed':
    case 'stage.unavailable':
      return patchStage(next, d.stage as StageKey, {
        status: ev.type === 'stage.failed' ? 'failed' : 'unavailable',
        error: d.message as string,
        finished_at: ev.at,
      })
    case 'geo.ready':
      return { ...next, geo: d as unknown as GeoSummary }
    case 'forecast.ready':
      return { ...next, forecast: d as unknown as PriceForecast }
    case 'decision.ready': {
      const decision = d as unknown as Decision
      return { ...next, decision, rating: decision.rating }
    }
    case 'run.finished':
      return {
        ...next,
        status: d.status as RunDetail['status'],
        error: (d.error as string | null) ?? null,
        finished_at: ev.at,
      }
    default:
      return next
  }
}

export function applyEventToCache(qc: QueryClient, runId: string, ev: RunEvent) {
  qc.setQueryData<RunDetail>(runKey(runId), (prev) => (prev ? applyEvent(prev, ev) : prev))
}

/**
 * Subscribes to a run's live events while it is in progress and patches the query cache, so
 * every panel derives its skeleton/ready/error state from one source. Completed runs are
 * served from the snapshot alone (no stream, SC-007).
 */
export function useRunStream(runId: string | undefined, active: boolean) {
  const qc = useQueryClient()
  useEffect(() => {
    if (!runId || !active || typeof EventSource === 'undefined') return
    const source = new EventSource(`/api/runs/${encodeURIComponent(runId)}/events`)
    const handler = (msg: MessageEvent<string>) => {
      const ev = JSON.parse(msg.data) as RunEvent
      applyEventToCache(qc, runId, ev)
      if (ev.type === 'run.finished') {
        source.close()
        void qc.invalidateQueries({ queryKey: runKey(runId) })
        void qc.invalidateQueries({ queryKey: ['runs'] })
      }
    }
    for (const t of EVENT_TYPES) source.addEventListener(t, handler as EventListener)
    return () => source.close()
  }, [runId, active, qc])
}
