import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useId, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { Button, cn, focusRing } from '../../components/ui'
import { api, ApiError, TICKER_RE } from '../../lib/api'
import { runKey } from '../../lib/runStream'
import { useHealth } from './ConfigBanner'

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const id = window.setTimeout(() => setV(value), ms)
    return () => window.clearTimeout(id)
  }, [value, ms])
  return v
}

function todayLocal(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const inputBase =
  'block h-11 w-full rounded-md border bg-surface px-3 text-sm text-fg placeholder:text-muted/70 transition-colors'

export function NewRunForm() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const health = useHealth()
  const ids = { ticker: useId(), date: useId(), tickerMsg: useId(), dateMsg: useId() }

  const [ticker, setTicker] = useState('')
  const [date, setDate] = useState('')
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({})

  const debounced = useDebounced(ticker.trim(), 300)
  const formatOk = TICKER_RE.test(debounced)
  const check = useQuery({
    queryKey: ['ticker', debounced],
    queryFn: () => api.validateTicker(debounced),
    enabled: formatOk,
    staleTime: 5 * 60_000,
    retry: false,
  })

  const settled = debounced === ticker.trim()
  const checking = ticker.trim() !== '' && (!settled || (formatOk && check.isFetching))
  const tickerError =
    serverErrors.ticker ??
    (settled && ticker.trim() && !formatOk
      ? "Use 1–10 letters or digits (dots and dashes allowed)."
      : settled && check.data && !check.data.valid
        ? (check.data.reason ?? 'Unsupported ticker.')
        : undefined)
  const dateError =
    serverErrors.date ?? (date && date > todayLocal() ? 'The analysis date cannot be in the future.' : undefined)

  const blocked = (health.data?.problems?.length ?? 0) > 0
  const canSubmit =
    !blocked && settled && formatOk && check.data?.valid === true && !dateError && !checking

  const create = useMutation({
    mutationFn: () => api.createRun({ ticker: ticker.trim().toUpperCase(), date: date || undefined }),
    onSuccess: (run) => {
      qc.setQueryData(runKey(run.id), run)
      void qc.invalidateQueries({ queryKey: ['runs'] })
      navigate(`/runs/${run.id}`)
    },
    onError: (err) => {
      if (err instanceof ApiError) setServerErrors(err.fieldErrors)
    },
  })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (canSubmit) create.mutate()
  }

  const formError =
    create.error && !(create.error instanceof ApiError && Object.keys(create.error.fieldErrors).length)
      ? create.error.message
      : null

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-4 sm:grid-cols-[1fr_12rem_auto] sm:items-start">
      <div>
        <label htmlFor={ids.ticker} className="mb-1.5 block text-xs font-medium text-muted">
          Ticker
        </label>
        <input
          id={ids.ticker}
          name="ticker"
          value={ticker}
          onChange={(e) => {
            setTicker(e.target.value.toUpperCase())
            setServerErrors(({ ticker: _t, ...rest }) => rest)
          }}
          placeholder="e.g. XOM"
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          maxLength={10}
          aria-invalid={tickerError ? true : undefined}
          aria-describedby={ids.tickerMsg}
          className={cn(
            inputBase,
            'font-medium tracking-wide uppercase',
            tickerError ? 'border-negative' : 'border-border',
            focusRing,
          )}
        />
        <p id={ids.tickerMsg} aria-live="polite" className="mt-1.5 min-h-4 text-xs">
          {checking ? (
            <span className="text-muted">Checking…</span>
          ) : tickerError ? (
            <span className="text-negative">{tickerError}</span>
          ) : check.data?.valid ? (
            <span className="text-muted">
              {check.data.name}
              {check.data.exchange ? ` · ${check.data.exchange}` : ''}
            </span>
          ) : (
            <span className="text-muted">US-listed stock or ETF</span>
          )}
        </p>
      </div>

      <div>
        <label htmlFor={ids.date} className="mb-1.5 block text-xs font-medium text-muted">
          Analysis date
        </label>
        <input
          id={ids.date}
          type="date"
          name="date"
          value={date}
          max={todayLocal()}
          onChange={(e) => {
            setDate(e.target.value)
            setServerErrors(({ date: _d, ...rest }) => rest)
          }}
          aria-invalid={dateError ? true : undefined}
          aria-describedby={ids.dateMsg}
          className={cn(inputBase, dateError ? 'border-negative' : 'border-border', focusRing)}
        />
        <p id={ids.dateMsg} aria-live="polite" className="mt-1.5 min-h-4 text-xs">
          {dateError ? (
            <span className="text-negative">{dateError}</span>
          ) : (
            <span className="text-muted">Blank = latest completed session</span>
          )}
        </p>
      </div>

      <div className="sm:pt-[1.375rem]">
        <Button type="submit" variant="primary" className="h-11 w-full sm:w-auto" disabled={!canSubmit} loading={create.isPending}>
          Analyze
        </Button>
      </div>

      {formError && (
        <p role="alert" className="text-sm text-negative sm:col-span-3">
          {formError}
        </p>
      )}
    </form>
  )
}
