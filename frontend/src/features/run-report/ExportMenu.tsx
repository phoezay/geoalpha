import { useEffect, useId, useRef, useState } from 'react'
import { Button, cn, focusRing } from '../../components/ui'
import { api, type RunDetail } from '../../lib/api'

const formats = [
  { format: 'md' as const, label: 'Markdown', hint: '.md, for notes and repos' },
  { format: 'html' as const, label: 'HTML page', hint: 'Self-contained, opens offline' },
]

/** Disclosure menu of download links (FR-025). Disabled until the run completes. */
export function ExportMenu({ run }: { run: RunDetail }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const menuId = useId()
  const ready = run.status === 'completed'

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        ref.current?.querySelector('button')?.focus()
      }
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={ref} className="relative">
      <span title={ready ? undefined : 'Available when the run completes'}>
        <Button
          size="sm"
          disabled={!ready}
          aria-expanded={open}
          aria-controls={menuId}
          onClick={() => setOpen((v) => !v)}
        >
          Export
          <svg aria-hidden="true" viewBox="0 0 12 12" className="size-3" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path d="m3 4.5 3 3 3-3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Button>
      </span>
      {open && (
        <ul
          id={menuId}
          className="absolute right-0 z-30 mt-1.5 w-56 overflow-hidden rounded-lg border border-border bg-surface p-1 shadow-lg shadow-black/5"
        >
          {formats.map((f) => (
            <li key={f.format}>
              <a
                href={api.exportUrl(run.id, f.format)}
                download
                onClick={() => setOpen(false)}
                className={cn('block rounded-md px-3 py-2 hover:bg-surface-2', focusRing)}
              >
                <span className="block text-sm font-medium text-fg">{f.label}</span>
                <span className="block text-xs text-muted">{f.hint}</span>
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
