import { clsx, type ClassValue } from 'clsx'
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react'

export const cn = (...v: ClassValue[]) => clsx(v)

export const focusRing =
  'focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg'

/* ------------------------------------------------------------------ Card */

export function Card({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cn('rounded-xl border border-border bg-surface', className)}
      {...props}
    />
  )
}

export function CardHeader({
  title,
  subtitle,
  action,
  id,
}: {
  title: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
  id?: string
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border px-4 py-3 sm:px-5">
      <div className="min-w-0">
        <h2 id={id} className="text-sm font-semibold text-fg">
          {title}
        </h2>
        {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

/* ---------------------------------------------------------------- Button */

type ButtonVariant = 'primary' | 'secondary' | 'ghost'

const buttonVariants: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-accent-fg hover:opacity-90 disabled:opacity-50',
  secondary:
    'border border-border bg-surface text-fg hover:bg-surface-2 disabled:opacity-50',
  ghost: 'text-muted hover:bg-surface-2 hover:text-fg disabled:opacity-50',
}

/** The only component allowed to show a spinner (Constitution IV). */
export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  className,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: 'sm' | 'md'
  loading?: boolean
}) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:cursor-not-allowed',
        size === 'sm' ? 'h-8 px-3 text-xs' : 'h-10 px-4 text-sm',
        buttonVariants[variant],
        focusRing,
        className,
      )}
      {...props}
    >
      {loading && (
        <span
          role="progressbar"
          aria-label="Working"
          className="size-3.5 animate-spin rounded-full border-2 border-current border-r-transparent motion-reduce:animate-none"
        />
      )}
      {children}
    </button>
  )
}

/* ----------------------------------------------------------------- Badge */

export type Tone = 'neutral' | 'accent' | 'positive' | 'negative' | 'warning'

const toneClasses: Record<Tone, string> = {
  neutral: 'bg-surface-2 text-muted',
  accent: 'bg-accent-soft text-accent',
  positive: 'bg-positive-soft text-positive',
  negative: 'bg-negative-soft text-negative',
  warning: 'bg-warning-soft text-warning',
}

export function Badge({
  tone = 'neutral',
  className,
  children,
}: {
  tone?: Tone
  className?: string
  children: ReactNode
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium whitespace-nowrap',
        toneClasses[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

/* ------------------------------------------------------------------ Stat */

export function Stat({
  label,
  value,
  tone = 'neutral',
  hint,
}: {
  label: string
  value: ReactNode
  tone?: Tone
  hint?: ReactNode
}) {
  const valueTone: Record<Tone, string> = {
    neutral: 'text-fg',
    accent: 'text-accent',
    positive: 'text-positive',
    negative: 'text-negative',
    warning: 'text-warning',
  }
  return (
    <div className="min-w-0">
      <div className="text-xs font-medium text-muted">{label}</div>
      <div className={cn('mt-1 text-2xl font-semibold tracking-tight', valueTone[tone])}>
        {value}
      </div>
      {hint && <div className="mt-0.5 text-xs text-muted">{hint}</div>}
    </div>
  )
}

/* ------------------------------------------------------- Empty / Error */

export function EmptyState({
  title,
  description,
  action,
  tone = 'neutral',
}: {
  title: string
  description?: ReactNode
  action?: ReactNode
  tone?: 'neutral' | 'warning'
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      <div
        aria-hidden="true"
        className={cn(
          'mb-1 grid size-9 place-items-center rounded-full text-base',
          tone === 'warning' ? 'bg-warning-soft text-warning' : 'bg-surface-2 text-muted',
        )}
      >
        {tone === 'warning' ? '!' : '○'}
      </div>
      <p className={cn('font-medium', tone === 'warning' ? 'text-warning' : 'text-fg')}>
        {title}
      </p>
      {description && <p className="max-w-sm text-xs text-muted">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  retryLabel = 'Retry',
}: {
  title?: string
  message?: ReactNode
  onRetry?: () => void
  retryLabel?: string
}) {
  return (
    <div
      role="alert"
      className="flex h-full flex-col items-center justify-center gap-2 px-6 py-10 text-center"
    >
      <div
        aria-hidden="true"
        className="mb-1 grid size-9 place-items-center rounded-full bg-negative-soft font-semibold text-negative"
      >
        ×
      </div>
      <p className="font-medium text-fg">{title}</p>
      {message && <p className="max-w-sm text-xs text-muted">{message}</p>}
      {onRetry && (
        <Button size="sm" className="mt-2" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  )
}

/* ------------------------------------------------------------ Disclaimer */

export function Disclaimer({ className }: { className?: string }) {
  return (
    <p className={cn('text-xs text-muted', className)}>
      Research output, not financial advice.
    </p>
  )
}
