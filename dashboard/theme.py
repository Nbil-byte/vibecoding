"""Design system untuk dashboard Vibe Coding.

Palet: Cerulean, Dark Slate Grey, Eggshell, Dark Goldenrod, Tuscan Sun.
Tema: light, hangat, editorial-analytical.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# --- Design tokens ---
CERULEAN = "#437C90"
DARK_SLATE = "#255957"
EGGSHELL = "#EEEBD3"
GOLDENROD = "#A98743"
TUSCAN = "#F7C548"

SURFACE = "#F8F7F0"
SURFACE_STRONG = "#FFFFFF"
TEXT_PRIMARY = "#203F3D"
TEXT_SECONDARY = "#60716F"
BORDER = "rgba(37, 89, 87, 0.16)"
GRIDLINE = "rgba(37, 89, 87, 0.12)"
NEGATIVE = "#B65C4A"

# --- Alias untuk kompatibilitas ---
LINE = GRIDLINE
TEXT = TEXT_PRIMARY
TEXT_MUTED = TEXT_SECONDARY
NEUTRAL = GOLDENROD

# --- Pemetaan semantik ---
SENTIMENT_COLORS = {
    "negative": NEGATIVE,
    "neutral": GOLDENROD,
    "positive": CERULEAN,
}

SENTIMENT_ORDER = ["negative", "neutral", "positive"]

# Palet kategorikal: berselang-seling agar kategori berdampingan kontras.
CATEGORICAL = [
    CERULEAN,
    GOLDENROD,
    DARK_SLATE,
    TUSCAN,
    NEGATIVE,
    "#6B9AAB",
    "#C4A862",
    "#3D7170",
    "#D4A53A",
    "#C97560",
]

# Heatmap: Eggshell → Dark Goldenrod → Cerulean → Dark Slate Grey
HEAT_SCALE = [
    [0.00, "#EEEBD3"],
    [0.25, "#A98743"],
    [0.50, "#437C90"],
    [0.75, "#3D7170"],
    [1.00, "#255957"],
]

# Diverging: negatif (brick) ke positif (cerulean)
DIVERGING = [
    [0.0, NEGATIVE],
    [0.5, GOLDENROD],
    [1.0, CERULEAN],
]

PLOTLY_TEMPLATE = "vibecoding"


def register_template() -> None:
    """Daftarkan template Plotly bertema light hangat."""
    axis = dict(
        gridcolor=GRIDLINE,
        zerolinecolor=GRIDLINE,
        linecolor="rgba(0,0,0,0)",
        tickfont=dict(color=TEXT_SECONDARY, size=11),
        title=dict(font=dict(color=TEXT_SECONDARY, size=12)),
        showline=False,
    )

    pio.templates[PLOTLY_TEMPLATE] = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="Inter, Manrope, Source Sans 3, Segoe UI, sans-serif",
                color=TEXT_PRIMARY,
                size=13,
            ),
            colorway=CATEGORICAL,
            colorscale=dict(sequential=HEAT_SCALE, diverging=DIVERGING),
            xaxis=axis,
            yaxis=axis,
            title=dict(font=dict(color=TEXT_PRIMARY, size=15, family="Inter, Manrope, sans-serif"), x=0, xanchor="left"),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                bordercolor="rgba(0,0,0,0)",
                borderwidth=0,
                font=dict(color=TEXT_SECONDARY, size=11),
                orientation="h",
                y=-0.15,
                x=0,
            ),
            hoverlabel=dict(
                bgcolor=SURFACE_STRONG,
                bordercolor=BORDER,
                font=dict(color=TEXT_PRIMARY, size=12),
            ),
            margin=dict(l=8, r=8, t=54, b=28),
            coloraxis=dict(
                colorbar=dict(outlinewidth=0, tickfont=dict(color=TEXT_SECONDARY, size=10)),
            ),
        )
    )
    pio.templates.default = PLOTLY_TEMPLATE


CSS = f"""
<style>
  :root {{
    --color-primary: {CERULEAN};
    --color-primary-dark: {DARK_SLATE};
    --color-background: {EGGSHELL};
    --color-secondary: {GOLDENROD};
    --color-accent: {TUSCAN};
    --color-surface: {SURFACE};
    --color-surface-strong: {SURFACE_STRONG};
    --color-text-primary: {TEXT_PRIMARY};
    --color-text-secondary: {TEXT_SECONDARY};
    --color-border: {BORDER};
    --color-negative: {NEGATIVE};
  }}

  .stApp {{
      background: {EGGSHELL};
  }}

  #MainMenu, footer, header {{ visibility: hidden; }}

  .block-container {{
      padding-top: 1.8rem; padding-bottom: 2rem;
      max-width: 1320px;
  }}

  h1, h2, h3, h4 {{
      color: {TEXT_PRIMARY};
      letter-spacing: -0.015em;
      font-family: Inter, Manrope, Source Sans 3, sans-serif;
  }}
  h1 {{ font-weight: 700; }}
  h2 {{ font-weight: 600; }}
  h3 {{ font-weight: 600; }}

  /* --- Hero section --- */
  .vc-hero {{
      background: {SURFACE_STRONG};
      border: 1px solid {BORDER};
      border-radius: 14px;
      padding: 1.4rem 1.8rem;
      margin-bottom: 1.4rem;
  }}
  .vc-hero-title {{
      font-size: 1.75rem;
      font-weight: 700;
      line-height: 1.2;
      margin: 0 0 .4rem 0;
      color: {DARK_SLATE};
  }}
  .vc-hero-sub {{
      color: {TEXT_SECONDARY};
      font-size: .95rem;
      line-height: 1.6;
      margin: 0;
      max-width: 72ch;
  }}
  .vc-hero-sub strong {{ color: {DARK_SLATE}; }}
  .vc-badge {{
      display: inline-block;
      font-size: .72rem;
      font-weight: 600;
      padding: .18rem .6rem;
      border-radius: 999px;
      margin-right: .35rem;
      background: rgba(67, 124, 144, 0.10);
      color: {CERULEAN};
  }}
  .vc-badge.accent {{ background: rgba(247, 197, 72, 0.18); color: #8A6A1A; }}

  /* --- KPI cards --- */
  .vc-kpi {{
      background: {SURFACE};
      border: 1px solid {BORDER};
      border-radius: 14px;
      padding: .9rem 1.1rem;
      height: 100%;
      box-shadow: 0 1px 3px rgba(37, 89, 87, 0.05);
  }}
  .vc-kpi.cerulean {{ border-top: 3px solid {CERULEAN}; }}
  .vc-kpi.goldenrod {{ border-top: 3px solid {GOLDENROD}; }}
  .vc-kpi.tuscan   {{ border-top: 3px solid {TUSCAN}; }}
  .vc-kpi.negative {{ border-top: 3px solid {NEGATIVE}; }}
  .vc-kpi-label {{
      color: {TEXT_SECONDARY};
      font-size: .72rem;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: .07em;
      margin-bottom: .3rem;
  }}
  .vc-kpi-value {{
      color: {TEXT_PRIMARY};
      font-size: 1.55rem;
      font-weight: 700;
      line-height: 1.15;
  }}
  .vc-kpi-delta {{
      font-size: .78rem;
      margin-top: .25rem;
      color: {TEXT_SECONDARY};
  }}
  .vc-kpi-delta.up {{ color: {CERULEAN}; }}
  .vc-kpi-delta.down {{ color: {NEGATIVE}; }}

  /* --- Narrative cards --- */
  .vc-card {{
      background: {SURFACE_STRONG};
      border: 1px solid {BORDER};
      border-radius: 12px;
      padding: 1.1rem 1.3rem;
      margin-bottom: .9rem;
  }}
  .vc-era-tag {{
      display: inline-block;
      font-size: .68rem;
      font-weight: 700;
      letter-spacing: .09em;
      text-transform: uppercase;
      padding: .18rem .55rem;
      border-radius: 999px;
      margin-bottom: .5rem;
  }}
  .vc-card p {{
      color: {TEXT_SECONDARY};
      line-height: 1.65;
      margin: .4rem 0 0 0;
      font-size: .9rem;
  }}
  .vc-card strong {{ color: {TEXT_PRIMARY}; }}
  .vc-card b.hl {{ color: {CERULEAN}; }}
  .vc-card h4 {{ margin: 0; font-size: 1rem; font-weight: 600; }}

  /* --- Callouts --- */
  .vc-callout {{
      border-radius: 10px;
      padding: .8rem 1.1rem;
      font-size: .87rem;
      line-height: 1.6;
      margin: .6rem 0 1rem 0;
  }}
  .vc-callout-title {{
      font-weight: 600;
      margin-bottom: .25rem;
      font-size: .88rem;
  }}
  .vc-callout p {{ margin: 0; }}
  .vc-callout.info {{
      background: rgba(67, 124, 144, 0.08);
      border-left: 3px solid {CERULEAN};
  }}
  .vc-callout.info .vc-callout-title {{ color: {CERULEAN}; }}
  .vc-callout.info p {{ color: {TEXT_SECONDARY}; }}
  .vc-callout.insight {{
      background: rgba(247, 197, 72, 0.10);
      border-left: 3px solid {TUSCAN};
  }}
  .vc-callout.insight .vc-callout-title {{ color: #8A6A1A; }}
  .vc-callout.insight p {{ color: {TEXT_SECONDARY}; }}
  .vc-callout.method {{
      background: rgba(169, 135, 67, 0.08);
      border-left: 3px solid {GOLDENROD};
  }}
  .vc-callout.method .vc-callout-title {{ color: {GOLDENROD}; }}
  .vc-callout.method p {{ color: {TEXT_SECONDARY}; }}
  .vc-callout.warn {{
      background: rgba(182, 92, 74, 0.07);
      border-left: 3px solid {NEGATIVE};
  }}
  .vc-callout.warn .vc-callout-title {{ color: {NEGATIVE}; }}
  .vc-callout.warn p {{ color: {TEXT_SECONDARY}; }}
  .vc-callout strong {{ color: {TEXT_PRIMARY}; }}

  /* --- Legacy callout aliases --- */
  .vc-note {{
      background: rgba(67, 124, 144, 0.08);
      border-left: 3px solid {CERULEAN};
      border-radius: 10px;
      padding: .8rem 1.1rem;
      color: {TEXT_SECONDARY};
      font-size: .87rem;
      line-height: 1.6;
      margin: .6rem 0 1rem 0;
  }}
  .vc-note strong {{ color: {TEXT_PRIMARY}; }}
  .vc-warn {{
      background: rgba(182, 92, 74, 0.07);
      border-left: 3px solid {NEGATIVE};
      border-radius: 10px;
      padding: .8rem 1.1rem;
      color: {TEXT_SECONDARY};
      font-size: .87rem;
      line-height: 1.6;
      margin: .6rem 0 1rem 0;
  }}
  .vc-warn strong {{ color: {TEXT_PRIMARY}; }}

  /* --- Sidebar --- */
  section[data-testid="stSidebar"] {{
      background: {DARK_SLATE};
      border-right: none;
  }}
  section[data-testid="stSidebar"] .block-container {{
      padding-top: 1.4rem;
      padding-left: 1rem;
      padding-right: 1rem;
  }}
  section[data-testid="stSidebar"] .stRadio label,
  section[data-testid="stSidebar"] .stCaption,
  section[data-testid="stSidebar"] span,
  section[data-testid="stSidebar"] p {{
      color: rgba(238, 235, 211, 0.85) !important;
  }}
  section[data-testid="stSidebar"] .stRadio label[data-checked="true"],
  section[data-testid="stSidebar"] [aria-checked="true"] {{
      background: rgba(247, 197, 72, 0.15);
      border-radius: 8px;
  }}
  section[data-testid="stSidebar"] hr {{
      border-color: rgba(238, 235, 211, 0.15);
  }}
  section[data-testid="stSidebar"] b {{
      color: {TUSCAN};
  }}

  /* --- Dataframe --- */
  [data-testid="stDataFrame"] {{
      border: 1px solid {BORDER};
      border-radius: 10px;
      overflow: hidden;
  }}
  [data-testid="stDataFrame"] table {{
      font-size: .85rem;
  }}
  [data-testid="stDataFrame"] thead th {{
      background: {SURFACE};
      color: {TEXT_PRIMARY};
      font-weight: 600;
      border-bottom: 1px solid {BORDER};
  }}
  [data-testid="stDataFrame"] tbody tr:nth-child(even) {{
      background: rgba(248, 247, 240, 0.5);
  }}

  /* --- Divider --- */
  hr {{ border-color: {BORDER}; }}

  /* --- Streamlit elements --- */
  .stMarkdown p {{ color: {TEXT_SECONDARY}; line-height: 1.65; }}
  .stMarkdown strong {{ color: {TEXT_PRIMARY}; }}
  .stCaption {{ color: {TEXT_SECONDARY} !important; }}
  .stSubheader {{ color: {TEXT_PRIMARY}; }}

  /* --- Plotly modebar --- */
  .modebar {{
      display: none !important;
  }}

  /* --- Download button --- */
  .stDownloadButton > button {{
      background: {CERULEAN};
      color: white;
      border: none;
      border-radius: 8px;
      font-weight: 500;
      font-size: .85rem;
      padding: .5rem 1.2rem;
  }}
  .stDownloadButton > button:hover {{
      background: {DARK_SLATE};
  }}

  /* --- Selectbox / slider / input --- */
  .stSelectbox > div > div,
  .stMultiSelect > div > div,
  .stTextInput > div > div > input {{
      border-radius: 8px;
      border-color: {BORDER};
  }}

  /* --- Responsive grid --- */
  @media (max-width: 768px) {{
      .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
      .vc-hero-title {{ font-size: 1.4rem; }}
  }}
</style>
"""


def kpi(label: str, value: str, delta: str = "", variant: str = "", direction: str = "") -> str:
    """HTML kartu KPI. `variant`: '', 'cerulean', 'goldenrod', 'tuscan', 'negative'.

    Untuk kompatibilitas mundur, 'turq' → 'cerulean', 'ice' → 'tuscan', 'rust' → 'negative'.
    """
    _map = {"turq": "cerulean", "ice": "tuscan", "rust": "negative"}
    v = _map.get(variant, variant)
    delta_cls = f"vc-kpi-delta {direction}".strip()
    delta_html = f'<div class="{delta_cls}">{delta}</div>' if delta else ""
    return (
        f'<div class="vc-kpi {v}">'
        f'<div class="vc-kpi-label">{label}</div>'
        f'<div class="vc-kpi-value">{value}</div>'
        f"{delta_html}"
        f"</div>"
    )


def era_card(tag: str, color: str, title: str, body: str) -> str:
    """HTML kartu narasi era."""
    return (
        f'<div class="vc-card">'
        f'<span class="vc-era-tag" style="background:{color}22;color:{color};">{tag}</span>'
        f"<h4>{title}</h4>"
        f"<p>{body}</p>"
        f"</div>"
    )


def callout(kind: str, title: str, body: str) -> str:
    """HTML callout. `kind`: 'info', 'insight', 'method', 'warn'."""
    return (
        f'<div class="vc-callout {kind}">'
        f'<div class="vc-callout-title">{title}</div>'
        f'<p>{body}</p>'
        f'</div>'
    )


def section_header(title: str, subtitle: str = "", badges: list[str] | None = None) -> str:
    """HTML section header dengan badge opsional."""
    badge_html = "".join(f'<span class="vc-badge">{b}</span>' for b in (badges or []))
    sub_html = f'<p class="vc-hero-sub" style="margin-top:.5rem">{subtitle}</p>' if subtitle else ""
    return (
        f'<div style="margin-bottom:1.2rem">'
        f'{badge_html}'
        f'<h2 style="margin:.3rem 0 0 0">{title}</h2>'
        f'{sub_html}'
        f'</div>'
    )
