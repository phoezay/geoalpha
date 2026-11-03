import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  LineSeries,
  LineStyle,
  type IChartApi,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import type { PriceForecast } from '../../lib/api'

/** Resolve a CSS colour (incl. oklch / var()) to rgba() the chart library can parse. */
function cssColor(varName: string, alpha = 1): string {
  const raw = getComputedStyle(document.documentElement).getPropertyValue(varName).trim() || '#888'
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 1
  const ctx = canvas.getContext('2d')
  if (!ctx) return raw
  ctx.fillStyle = raw
  ctx.fillRect(0, 0, 1, 1)
  const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function palette() {
  return {
    text: cssColor('--ga-muted'),
    grid: cssColor('--ga-border', 0.6),
    surface: cssColor('--ga-surface'),
    accent: cssColor('--ga-accent'),
    band: cssColor('--ga-accent', 0.16),
    up: cssColor('--ga-positive'),
    down: cssColor('--ga-negative'),
  }
}

export function ForecastChart({ forecast, analysisDate }: { forecast: PriceForecast; analysisDate: string }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    let chart: IChartApi | null = createChart(ref.current, { autoSize: true })

    // Order = z-order: band first (p90 area, then a surface-coloured p10 area masking below it).
    const upper = chart.addSeries(AreaSeries, { lineVisible: false, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
    const lower = chart.addSeries(AreaSeries, { lineVisible: false, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false })
    const median = chart.addSeries(LineSeries, { lineWidth: 2, lineStyle: LineStyle.Dashed, priceLineVisible: false, title: 'p50' })
    const candles = chart.addSeries(CandlestickSeries, { priceLineVisible: false })

    const apply = () => {
      if (!chart) return
      const c = palette()
      chart.applyOptions({
        layout: { background: { type: ColorType.Solid, color: c.surface }, textColor: c.text, fontFamily: 'Inter, ui-sans-serif, system-ui', attributionLogo: true },
        grid: { vertLines: { color: c.grid }, horzLines: { color: c.grid } },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false },
        crosshair: { vertLine: { labelBackgroundColor: c.accent }, horzLine: { labelBackgroundColor: c.accent } },
      })
      upper.applyOptions({ topColor: c.band, bottomColor: c.band })
      lower.applyOptions({ topColor: c.surface, bottomColor: c.surface })
      median.applyOptions({ color: c.accent })
      candles.applyOptions({ upColor: c.up, downColor: c.down, borderUpColor: c.up, borderDownColor: c.down, wickUpColor: c.up, wickDownColor: c.down })
    }
    apply()

    // 60 sessions of context keeps the 5-session band readable next to the candles.
    const history = forecast.history.slice(-60)
    const last = history[history.length - 1]
    const anchor = last ? [{ time: last.date, value: last.close }] : []
    candles.setData(history.map((b) => ({ time: b.date, open: b.open, high: b.high, low: b.low, close: b.close })))
    upper.setData([...anchor, ...forecast.path.map((x) => ({ time: x.date, value: x.p90 }))])
    lower.setData([...anchor, ...forecast.path.map((x) => ({ time: x.date, value: x.p10 }))])
    median.setData([...anchor, ...forecast.path.map((x) => ({ time: x.date, value: x.p50 }))])
    if (last) {
      createSeriesMarkers(candles, [
        { time: last.date, position: 'aboveBar', shape: 'arrowDown', color: palette().accent, text: analysisDate === last.date ? 'As of' : 'Last bar' },
      ])
    }
    chart.timeScale().applyOptions({ rightOffset: 2 })
    chart.timeScale().fitContent()

    const onTheme = () => requestAnimationFrame(apply)
    window.addEventListener('geoalpha:theme', onTheme)
    return () => {
      window.removeEventListener('geoalpha:theme', onTheme)
      chart?.remove()
      chart = null
    }
  }, [forecast, analysisDate])

  return (
    // A figure, not role="img": the chart library renders its attribution link inside.
    <figure className="m-0 h-full w-full">
      <figcaption className="sr-only">
        {`Price chart: ${Math.min(60, forecast.history.length)} days of history and a ${forecast.horizon}-session forecast band`}
      </figcaption>
      <div ref={ref} className="h-full w-full" />
    </figure>
  )
}
