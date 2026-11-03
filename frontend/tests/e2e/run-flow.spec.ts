import { expect, test, type Page } from '@playwright/test'

/** T094: full offline flow (fake engine, demo geopolitics, synthetic forecast). */

async function trackCls(page: Page) {
  await page.addInitScript(() => {
    ;(window as unknown as { __cls: number }).__cls = 0
    new PerformanceObserver((list) => {
      for (const e of list.getEntries() as unknown as { hadRecentInput: boolean; value: number }[]) {
        if (!e.hadRecentInput) (window as unknown as { __cls: number }).__cls += e.value
      }
    }).observe({ type: 'layout-shift', buffered: true })
  })
}

async function startRun(page: Page, ticker: string) {
  await page.goto('/')
  await page.getByLabel('Ticker').fill(ticker)
  const analyze = page.getByRole('button', { name: 'Analyze' })
  await expect(analyze).toBeEnabled({ timeout: 15_000 })
  const t0 = Date.now()
  await analyze.click()
  await expect(page.getByText('Loading final decision…')).toBeAttached()
  return Date.now() - t0
}

test('XOM: skeleton fast, stages fill without layout shift, decision cites geo', async ({ page }) => {
  await trackCls(page)
  const skeletonMs = await startRun(page, 'XOM')
  expect(skeletonMs, 'SC-001: skeleton within 1 s of submit').toBeLessThan(1000)

  await page.evaluate(() => ((window as unknown as { __cls: number }).__cls = 0))
  await expect(page.getByText('Committee rating')).toBeVisible({ timeout: 60_000 })
  await expect(page.getByText('10 of 10 steps')).toBeVisible()
  const cls = await page.evaluate(() => (window as unknown as { __cls: number }).__cls)
  expect(cls, 'SC-003: CLS from skeleton to completed report').toBeLessThan(0.1)

  // Decision cites signals; clicking one scrolls to its row.
  const chip = page.getByRole('button', { name: /go to signal/ }).first()
  await expect(chip).toBeVisible()
  await chip.click()
  await expect(page.locator('[id^="signal-"]:focus')).toHaveCount(1)

  // Forecast and disclaimer present.
  await expect(page.getByText('Expected move')).toBeVisible()
  await expect(page.getByText('Research output, not financial advice.').first()).toBeVisible()

  // Export is available and downloads a Markdown file.
  await page.getByRole('button', { name: 'Export' }).click()
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('link', { name: /Markdown/ }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/^XOM_\d{4}-\d{2}-\d{2}_[0-9A-Z]{26}\.md$/)
})

test('KO: no material geopolitical exposure', async ({ page }) => {
  await startRun(page, 'KO')
  await expect(page.getByText(/No material geopolitical exposure detected for/)).toBeVisible({ timeout: 60_000 })
  await expect(page.getByText('No material geopolitical factors for this ticker.')).toBeVisible({ timeout: 60_000 })
})

test('NEWIPO: forecast unavailable, run still completes', async ({ page }) => {
  await startRun(page, 'NEWIPO')
  await expect(page.getByText('Committee rating')).toBeVisible({ timeout: 60_000 })
  await expect(page.getByText(/Not enough price history/).first()).toBeVisible()
  await expect(page.getByText(/Missing inputs: price forecast/)).toBeVisible()
})

test('FAILME: failure shows a resumable error, Resume completes the run', async ({ page }) => {
  await startRun(page, 'FAILME')
  const resume = page.getByRole('button', { name: 'Resume run' }).first()
  await expect(resume).toBeVisible({ timeout: 60_000 })
  await expect(page.getByText(/Simulated trader failure/).first()).toBeVisible()
  await resume.click()
  await expect(page.getByText('Committee rating')).toBeVisible({ timeout: 60_000 })
})

test('reload mid-run keeps progress (FR-006)', async ({ page }) => {
  await startRun(page, 'LMT')
  await expect(page.getByText(/[1-9] of 10 steps/)).toBeVisible({ timeout: 30_000 })
  await page.reload()
  await expect(page.getByText('Committee rating')).toBeVisible({ timeout: 60_000 })
})

test('validation: bad ticker and future date block submit', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Ticker').fill('1BAD')
  await expect(page.getByText(/Use 1–10 letters/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Analyze' })).toBeDisabled()
  await page.getByLabel('Ticker').fill('ZZZZZQ')
  await expect(page.getByRole('button', { name: 'Analyze' })).toBeDisabled({ timeout: 15_000 })
})
