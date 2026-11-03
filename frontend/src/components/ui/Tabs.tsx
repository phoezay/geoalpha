import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { cn, focusRing } from './index'

export type TabItem = { key: string; label: ReactNode; badge?: ReactNode; content: ReactNode }

/** WAI-ARIA tabs with roving tabindex (arrow keys, Home/End). */
export function Tabs({ items, label }: { items: TabItem[]; label: string }) {
  const [active, setActive] = useState(items[0]?.key ?? '')
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})
  const base = useId()

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = items.findIndex((t) => t.key === active)
    const next =
      e.key === 'ArrowRight'
        ? (i + 1) % items.length
        : e.key === 'ArrowLeft'
          ? (i - 1 + items.length) % items.length
          : e.key === 'Home'
            ? 0
            : e.key === 'End'
              ? items.length - 1
              : -1
    if (next < 0) return
    e.preventDefault()
    const key = items[next]!.key
    setActive(key)
    refs.current[key]?.focus()
  }

  return (
    <div>
      <div
        role="tablist"
        aria-label={label}
        onKeyDown={onKeyDown}
        className="flex gap-1 overflow-x-auto border-b border-border px-2 sm:px-3"
      >
        {items.map((t) => {
          const selected = t.key === active
          return (
            <button
              key={t.key}
              ref={(el) => {
                refs.current[t.key] = el
              }}
              role="tab"
              type="button"
              id={`${base}-tab-${t.key}`}
              aria-selected={selected}
              aria-controls={`${base}-panel-${t.key}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(t.key)}
              className={cn(
                '-mb-px inline-flex h-11 shrink-0 items-center gap-2 border-b-2 px-3 text-sm font-medium transition-colors',
                selected
                  ? 'border-accent text-fg'
                  : 'border-transparent text-muted hover:text-fg',
                focusRing,
                'rounded-t-md',
              )}
            >
              {t.label}
              {t.badge}
            </button>
          )
        })}
      </div>
      {items.map((t) => (
        <div
          key={t.key}
          role="tabpanel"
          id={`${base}-panel-${t.key}`}
          aria-labelledby={`${base}-tab-${t.key}`}
          hidden={t.key !== active}
          tabIndex={0}
          className={cn('rounded-b-xl', focusRing)}
        >
          {t.content}
        </div>
      ))}
    </div>
  )
}
