import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

/** T095: accessibility, 360px layout, reduced motion, keyboard, no stray spinners. */

let runUrl = ''

test.beforeAll(async ({ browser }) => {
  const page = await browser.newPage()
  await page.goto('/')
  await page.getByLabel('Ticker').fill('XOM')
  await expect(page.getByRole('button', { name: 'Analyze' })).toBeEnabled({ timeout: 15_000 })
  await page.getByRole('button', { name: 'Analyze' }).click()
  await expect(page.getByText('Committee rating')).toBeVisible({ timeout: 60_000 })
  runUrl = new URL(page.url()).pathname
  await page.close()
})

const routes = () => ['/', runUrl, '/history']

async function setTheme(page: Page, theme: 'light' | 'dark') {
  await page.addInitScript((t) => {
    try {
      localStorage.setItem('geoalpha-theme', t)
    } catch {
      /* ignore */
    }
  }, theme)
}

for (const theme of ['light', 'dark'] as const) {
  test(`axe: no serious or critical violations (${theme})`, async ({ page }) => {
    await setTheme(page, theme)
    for (const path of routes()) {
      await page.goto(path)
      await page.waitForLoadState('networkidle')
      const results = await new AxeBuilder({ page }).analyze()
      const bad = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
      expect(bad.map((v) => `${path}: ${v.id} (${v.nodes.length})`)).toEqual([])
    }
  })
}

test('360px: no horizontal page scroll on any route', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 })
  for (const path of routes()) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    const width = await page.evaluate(() => document.scrollingElement!.scrollWidth)
    expect(width, path).toBeLessThanOrEqual(360)
  }
})

test('reduced motion: skeletons are static', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.route('**/api/runs?**', async (route) => {
    await new Promise((r) => setTimeout(r, 1500))
    await route.continue()
  })
  await page.goto('/history')
  const skeleton = page.locator('[data-skeleton]').first()
  await expect(skeleton).toBeAttached()
  expect(await skeleton.evaluate((el) => getComputedStyle(el).animationName)).toBe('none')
})

test('no progressbar outside buttons; keyboard reaches controls with visible focus', async ({ page }) => {
  await page.goto(runUrl)
  await expect(page.getByText('Committee rating')).toBeVisible()
  expect(await page.locator('[role="progressbar"]:not(button [role="progressbar"])').count()).toBe(0)

  await page.goto('/')
  await page.keyboard.press('Tab') // skip link
  await page.keyboard.press('Tab')
  const focused = page.locator(':focus')
  await expect(focused).toBeVisible()
  const ring = await focused.evaluate((el) => getComputedStyle(el).boxShadow)
  expect(ring).not.toBe('none')
})
