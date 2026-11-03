import { NavLink, Outlet, ScrollRestoration } from 'react-router'
import { cn, Disclaimer, focusRing } from '../components/ui'
import { ThemeToggle } from '../components/ui/ThemeToggle'

const nav = [
  { to: '/', label: 'New analysis', end: true },
  { to: '/history', label: 'History', end: false },
]

export function AppShell() {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className={cn(
          'sr-only rounded-md bg-surface px-3 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50',
          focusRing,
        )}
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-20 border-b border-border bg-bg/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:px-6">
          <NavLink to="/" className={cn('flex items-center gap-2 rounded-md', focusRing)}>
            <span aria-hidden="true" className="grid size-7 place-items-center rounded-lg bg-accent">
              <span className="size-3 rounded-full border-2 border-accent-fg" />
            </span>
            <span className="text-[15px] font-semibold tracking-tight">GeoAlpha</span>
          </NavLink>
          <nav aria-label="Primary" className="ml-2 flex items-center gap-1 sm:ml-6">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  cn(
                    'rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors sm:px-3',
                    isActive ? 'bg-surface-2 text-fg' : 'text-muted hover:text-fg',
                    focusRing,
                  )
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
        <Outlet />
      </main>
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-4 sm:px-6">
          <Disclaimer />
          <p className="text-xs text-muted">
            Built on TradingAgents · Kronos · WorldMonitor
          </p>
        </div>
      </footer>
      <ScrollRestoration />
    </div>
  )
}
