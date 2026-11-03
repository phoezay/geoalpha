"""Report export (FR-025): Markdown, and a single self-contained HTML page.

Agent text is model output, so the HTML renderer runs markdown-it with raw HTML disabled:
anything HTML-like in a report is escaped, never interpreted.
"""

from __future__ import annotations

import html
from datetime import UTC, datetime

from markdown_it import MarkdownIt

from geoalpha.api import schemas

_md = MarkdownIt("commonmark", {"html": False, "linkify": False}).enable("table")

_IMPACT = {"positive": "Tailwind", "negative": "Headwind", "mixed": "Mixed", "uncertain": "Unclear"}
_ALIGN = {
    "supports": "The price model supports this rating.",
    "contradicts": "The price model points the other way.",
    "neutral": "The price model expects little movement.",
    "unavailable": "No price-model forecast was available.",
}


def filename(run: schemas.RunDetail, ext: str) -> str:
    return f"{run.ticker}_{run.analysis_date.isoformat()}_{run.id}.{ext}"


def _stage(run: schemas.RunDetail, key: str) -> schemas.Stage:
    return next(s for s in run.stages if s.key == key)


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(run: schemas.RunDetail) -> str:
    d = run.decision
    out: list[str] = [
        f"# GeoAlpha report: {run.ticker}",
        "",
        f"- **Analysis date:** {run.analysis_date.isoformat()}"
        + (
            f" (requested {run.requested_date.isoformat()})"
            if run.requested_date != run.analysis_date
            else ""
        ),
        f"- **Run:** `{run.id}` · finished {run.finished_at.isoformat() if run.finished_at else 'n/a'}",
        f"- **Provider / models:** {run.llm_provider} · {run.deep_model} / {run.quick_model}",
        f"- **Exported:** {datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
        f"> {schemas.DISCLAIMER}",
        "",
        "## Decision",
        "",
    ]
    if d:
        out += [
            f"**Rating: {d.rating}** · {d.confidence.capitalize()} confidence",
            "",
            d.summary,
            "",
            f"- {_ALIGN[d.forecast_alignment]}",
        ]
        if d.geo_statement == "cites":
            out.append(f"- Geopolitical factors cited: {', '.join(d.cited_signal_ids)}")
        elif d.geo_statement == "none_material":
            out.append("- No material geopolitical factors for this ticker.")
        else:
            out.append("- Geopolitical data was unavailable for this run.")
        if d.missing_inputs:
            out.append(
                f"- Missing inputs: {', '.join(d.missing_inputs)} (confidence capped at medium)"
            )
        out += ["", "### Portfolio manager rationale", "", d.rationale_md]
    else:
        out.append("_No decision was produced._")

    out += ["", "## Geopolitical signals", ""]
    g = run.geo
    if g is None or g.materiality == "unavailable":
        reason = (
            g.unavailable_reason if g and g.unavailable_reason else "Not available for this run."
        )
        out.append(f"_{reason}_")
    elif not g.signals:
        out.append("_No material geopolitical exposure detected._")
    else:
        out += [
            "| # | Region | Category | Severity | Impact | Signal | Valid | Source |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for s in g.signals:
            src = (
                f"[{_cell(s.source_label)}]({s.source_url})"
                if s.source_url
                else _cell(s.source_label)
            )
            out.append(
                f"| {s.rank} | {_cell(s.region)} | {s.category} | {s.severity}/5 | "
                f"{_IMPACT[s.impact_direction]} | {_cell(s.headline)} | "
                f"{s.valid_at.date().isoformat()} | {src} |"
            )
        out += ["", "Rationale by signal:", ""]
        out += [f"- **{s.rank}. {s.headline}**: {s.rationale}" for s in g.signals]

    out += ["", "## Price forecast", ""]
    f = run.forecast
    if f is None:
        st = _stage(run, "forecast")
        out.append(f"_{st.error or 'No forecast for this run.'}_")
    else:
        out += [
            f"{f.model}, {f.sample_count} sample paths, next {f.horizon} sessions.",
            "",
            f"- Last close: {f.last_close:.2f}",
            f"- Expected move: {f.expected_move_pct:+.2f}%",
            f"- p10–p90 at horizon: {f.range_low:.2f}–{f.range_high:.2f}",
            "",
            "| Date | p10 | p50 | p90 |",
            "|---|---|---|---|",
        ]
        out += [
            f"| {p.date.isoformat()} | {p.p10:.2f} | {p.p50:.2f} | {p.p90:.2f} |" for p in f.path
        ]

    out += ["", "## Analyst reports", ""]
    for key, label in (
        ("market", "Market"),
        ("sentiment", "Sentiment"),
        ("news", "News"),
        ("fundamentals", "Fundamentals"),
    ):
        out += [f"### {label}", "", _stage(run, key).report_md or "_No report._", ""]

    debate = _stage(run, "research_debate")
    p = debate.payload or {}
    out += [
        "## Bull vs Bear debate",
        "",
        "### Bull",
        "",
        str(p.get("bull_history") or "_n/a_"),
        "",
        "### Bear",
        "",
        str(p.get("bear_history") or "_n/a_"),
        "",
        "### Research Manager",
        "",
        str(p.get("judge") or debate.report_md or "_n/a_"),
        "",
    ]

    risk = _stage(run, "risk_debate").payload or {}
    out += ["## Trader & risk review", "", _stage(run, "trader").report_md or "_No proposal._", ""]
    for k in ("aggressive", "conservative", "neutral"):
        if risk.get(k):
            out += [f"### {k.capitalize()} view", "", str(risk[k]), ""]

    out += ["---", "", f"_{schemas.DISCLAIMER} Generated by GeoAlpha._", ""]
    return "\n".join(out)


def _sparkline(f: schemas.PriceForecast) -> str:
    hist = [b.close for b in f.history[-60:]]
    pts = hist + [p.p50 for p in f.path]
    lo = min(min(hist), *(p.p10 for p in f.path))
    hi = max(max(hist), *(p.p90 for p in f.path))
    w, h, n = 640, 160, len(pts)

    def x(i: float) -> float:
        return float(8 + i * (w - 16) / max(1, n - 1))

    def y(v: float) -> float:
        return float(8 + (hi - v) * (h - 16) / max(1e-9, hi - lo))

    line = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(hist))
    k = len(hist) - 1
    upper = [(x(k), y(hist[-1]))] + [(x(k + 1 + i), y(p.p90)) for i, p in enumerate(f.path)]
    lower = [(x(k + 1 + i), y(p.p10)) for i, p in enumerate(f.path)][::-1] + [(x(k), y(hist[-1]))]
    band = " ".join(f"{a:.1f},{b:.1f}" for a, b in upper + lower)
    med = " ".join(
        f"{x(k + i):.1f},{y(v):.1f}" for i, v in enumerate([hist[-1], *[p.p50 for p in f.path]])
    )
    return (
        f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Price history and forecast band" '
        f'style="width:100%;height:auto">'
        f'<polygon points="{band}" fill="#4f46e5" fill-opacity="0.15"/>'
        f'<polyline points="{line}" fill="none" stroke="#525252" stroke-width="1.5"/>'
        f'<polyline points="{med}" fill="none" stroke="#4f46e5" stroke-width="2" stroke-dasharray="5 4"/>'
        f'<line x1="{x(k):.1f}" x2="{x(k):.1f}" y1="0" y2="{h}" stroke="#a3a3a3" stroke-dasharray="2 3"/>'
        "</svg>"
    )


_CSS = """
:root{color-scheme:light}*{box-sizing:border-box}
body{margin:0;background:#fafafa;color:#171717;font:14px/1.6 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:26px;letter-spacing:-.02em;margin:0 0 8px}h2{font-size:18px;margin:36px 0 12px;padding-top:20px;border-top:1px solid #e5e5e5}
h3{font-size:15px;margin:20px 0 6px}a{color:#4f46e5}blockquote{margin:12px 0;padding:8px 14px;border-left:3px solid #d97706;background:#fffbeb;color:#92400e}
table{border-collapse:collapse;width:100%;font-size:12.5px;display:block;overflow-x:auto}th,td{border-bottom:1px solid #e5e5e5;padding:6px 8px;text-align:left;vertical-align:top}
th{color:#525252;font-weight:600}code{background:#f5f5f5;padding:1px 4px;border-radius:4px;font-size:12px}
.card{background:#fff;border:1px solid #e5e5e5;border-radius:12px;padding:16px 18px;margin:12px 0}
"""


def render_html(run: schemas.RunDetail) -> str:
    body = _md.render(render_markdown(run))
    chart = (
        f'<div class="card">{_sparkline(run.forecast)}</div>'
        if run.forecast and run.forecast.history
        else ""
    )
    if chart:
        body = body.replace("<h2>Price forecast</h2>", f"<h2>Price forecast</h2>{chart}", 1)
    title = html.escape(f"GeoAlpha · {run.ticker} · {run.analysis_date.isoformat()}")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title><style>{_CSS}</style></head>"
        f"<body><main>{body}</main></body></html>"
    )
