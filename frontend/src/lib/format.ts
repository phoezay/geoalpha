import type { Tone } from '../components/ui'
import type { Rating, RunStatus } from './api'

export function ratingTone(r: Rating | null | undefined): Tone {
  if (r === 'Buy' || r === 'Overweight') return 'positive'
  if (r === 'Sell' || r === 'Underweight') return 'negative'
  return 'neutral'
}

export const statusLabel: Record<RunStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  interrupted: 'Interrupted',
}

export function statusTone(s: RunStatus): Tone {
  if (s === 'completed') return 'positive'
  if (s === 'failed') return 'negative'
  if (s === 'interrupted') return 'warning'
  return 'accent'
}

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y!, m! - 1, d!).toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })

export function relativeTime(iso: string, now = Date.now()): string {
  const diff = (new Date(iso).getTime() - now) / 1000
  const abs = Math.abs(diff)
  if (abs < 45) return 'just now'
  if (abs < 3600) return rtf.format(Math.round(diff / 60), 'minute')
  if (abs < 86400) return rtf.format(Math.round(diff / 3600), 'hour')
  return rtf.format(Math.round(diff / 86400), 'day')
}

export function duration(startIso?: string | null, endIso?: string | null): string | null {
  if (!startIso || !endIso) return null
  const s = Math.max(0, Math.round((new Date(endIso).getTime() - new Date(startIso).getTime()) / 1000))
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}
