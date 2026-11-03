import { Card } from '../components/ui'
import { RecentRuns } from '../features/history/RecentRuns'
import { ConfigBanner } from '../features/new-run/ConfigBanner'
import { NewRunForm } from '../features/new-run/NewRunForm'

const steps = [
  { title: 'Geopolitics', body: 'Exposure-aware signals with sources' },
  { title: 'Price model', body: 'Kronos forecast with an uncertainty band' },
  { title: 'Agent committee', body: 'Analysts, bull/bear debate, trader and risk review' },
]

export function NewRunPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Analyze a ticker</h1>
        <p className="mt-2 max-w-2xl text-muted">
          A multi-agent trading committee that weighs geopolitical risk and a price-model
          forecast, and shows the evidence behind every call.
        </p>
      </div>

      <ConfigBanner />

      <Card className="p-4 sm:p-6">
        <NewRunForm />
        <ol className="mt-6 grid gap-3 border-t border-border pt-5 sm:grid-cols-3">
          {steps.map((s, i) => (
            <li key={s.title} className="flex gap-3">
              <span
                aria-hidden="true"
                className="grid size-6 shrink-0 place-items-center rounded-full bg-accent-soft text-xs font-semibold text-accent"
              >
                {i + 1}
              </span>
              <div>
                <p className="text-sm font-medium">{s.title}</p>
                <p className="text-xs text-muted">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Card>

      <RecentRuns />
    </div>
  )
}
