"""Palet warna, template Plotly, dan CSS untuk dashboard.

Palet inti (ditentukan pengguna):
    AF3800  Rusty Spice
    FE621D  Blaze Orange
    FD5200  Flame Orange
    00CFC1  Turquoise
    00FFE7  Neon Ice

Warna turunan (INK, SURFACE, MUTED, dst.) dihitung sebagai latar dan teks
netral. Palet inti seluruhnya jenuh dan bersuhu tinggi, sehingga tidak ada
yang layak dipakai sebagai latar atau sebagai kategori "netral" tanpa
merusak keterbacaan. Warna netral karena itu diambil dari warna hangat
gelap yang serasi dengan oranye, bukan gray murni.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

# --- Palet inti ---
RUSTY = "#AF3800"
BLAZE = "#FE621D"
FLAME = "#FD5200"
TURQUOISE = "#00CFC1"
NEON_ICE = "#00FFE7"

# --- Netral turunan ---
INK = "#100A08"        # latar terluar
SURFACE = "#1B110E"    # latar kartu
SURFACE_ALT = "#241713" # latar kartu tersorot
LINE = "#3A241D"       # garis pembatas / grid
TEXT = "#F7EFEB"       # teks utama
TEXT_MUTED = "#B49E95" # teks sekunder
NEUTRAL = "#8A7A74"    # kategori "netral" pada grafik sentimen

# --- Pemetaan semantik ---
SENTIMENT_COLORS = {
    "negative": RUSTY,
    "neutral": NEUTRAL,
    "positive": TURQUOISE,
}

SENTIMENT_ORDER = ["negative", "neutral", "positive"]

# Urutan kategorikal: oranye dan turquoise dibuat berselang-seling agar
# kategori yang berdampingan selalu kontras.
CATEGORICAL = [
    BLAZE,
    TURQUOISE,
    RUSTY,
    NEON_ICE,
    FLAME,
    "#7FD8D2",
    "#D2691E",
    "#3FE9DC",
    "#8C2D00",
    "#B4E9E4",
]

# Skala kontinu "panas ke dingin", dipakai untuk heatmap.
HEAT_SCALE = [
    [0.00, INK],
    [0.20, RUSTY],
    [0.45, FLAME],
    [0.65, BLAZE],
    [0.85, TURQUOISE],
    [1.00, NEON_ICE],
]

# Skala diverging: negatif (rusty) ke positif (neon ice).
DIVERGING = [
    [0.0, RUSTY],
    [0.5, NEUTRAL],
    [1.0, NEON_ICE],
]

PLOTLY_TEMPLATE = "vibecoding"


def register_template() -> None:
    """Daftarkan template Plotly bertema palet ini."""
    axis = dict(
        gridcolor=LINE,
        zerolinecolor=LINE,
        linecolor=LINE,
        tickfont=dict(color=TEXT_MUTED, size=11),
        title=dict(font=dict(color=TEXT_MUTED, size=12)),
    )

    pio.templates[PLOTLY_TEMPLATE] = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="Inter, Segoe UI, system-ui, sans-serif",
                color=TEXT,
                size=12,
            ),
            colorway=CATEGORICAL,
            colorscale=dict(sequential=HEAT_SCALE, diverging=DIVERGING),
            xaxis=axis,
            yaxis=axis,
            title=dict(font=dict(color=TEXT, size=16), x=0, xanchor="left"),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                bordercolor=LINE,
                borderwidth=0,
                font=dict(color=TEXT_MUTED, size=11),
            ),
            hoverlabel=dict(
                bgcolor=SURFACE_ALT,
                bordercolor=BLAZE,
                font=dict(color=TEXT, size=12),
            ),
            margin=dict(l=10, r=10, t=50, b=10),
        )
    )
    pio.templates.default = PLOTLY_TEMPLATE


CSS = f"""
<style>
  .stApp {{
      background:
        radial-gradient(1200px 600px at 12% -8%, rgba(254,98,29,0.10), transparent 60%),
        radial-gradient(900px 500px at 88% 4%, rgba(0,207,193,0.08), transparent 60%),
        {INK};
  }}

  #MainMenu, footer, header {{ visibility: hidden; }}

  .block-container {{ padding-top: 2.2rem; max-width: 1400px; }}

  h1, h2, h3, h4 {{ color: {TEXT}; letter-spacing: -0.02em; }}

  /* --- Judul hero --- */
  .vc-hero {{
      background: linear-gradient(135deg, rgba(175,56,0,0.30), rgba(0,207,193,0.12));
      border: 1px solid {LINE};
      border-radius: 18px;
      padding: 1.8rem 2rem;
      margin-bottom: 1.6rem;
  }}
  .vc-hero-title {{
      font-size: 2.15rem;
      font-weight: 750;
      line-height: 1.15;
      margin: 0 0 .5rem 0;
      background: linear-gradient(100deg, {NEON_ICE}, {TURQUOISE} 28%, {BLAZE} 72%, {FLAME});
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
  }}
  .vc-hero-sub {{ color: {TEXT_MUTED}; font-size: 1rem; margin: 0; max-width: 70ch; }}

  /* --- Kartu KPI --- */
  .vc-kpi {{
      background: linear-gradient(160deg, {SURFACE_ALT}, {SURFACE});
      border: 1px solid {LINE};
      border-left: 3px solid {BLAZE};
      border-radius: 12px;
      padding: 1rem 1.1rem;
      height: 100%;
  }}
  .vc-kpi.turq {{ border-left-color: {TURQUOISE}; }}
  .vc-kpi.ice  {{ border-left-color: {NEON_ICE}; }}
  .vc-kpi.rust {{ border-left-color: {RUSTY}; }}
  .vc-kpi-label {{
      color: {TEXT_MUTED};
      font-size: .72rem;
      text-transform: uppercase;
      letter-spacing: .09em;
      margin-bottom: .35rem;
  }}
  .vc-kpi-value {{ color: {TEXT}; font-size: 1.75rem; font-weight: 700; line-height: 1.1; }}
  .vc-kpi-delta {{ font-size: .78rem; margin-top: .3rem; color: {TEXT_MUTED}; }}
  .vc-kpi-delta.up {{ color: {NEON_ICE}; }}
  .vc-kpi-delta.down {{ color: {FLAME}; }}

  /* --- Kartu narasi --- */
  .vc-card {{
      background: {SURFACE};
      border: 1px solid {LINE};
      border-radius: 14px;
      padding: 1.25rem 1.4rem;
      margin-bottom: 1rem;
  }}
  .vc-era-tag {{
      display: inline-block;
      font-size: .7rem;
      font-weight: 700;
      letter-spacing: .1em;
      text-transform: uppercase;
      padding: .2rem .6rem;
      border-radius: 999px;
      margin-bottom: .6rem;
  }}
  .vc-card p {{ color: {TEXT_MUTED}; line-height: 1.68; margin: .45rem 0 0 0; }}
  .vc-card strong {{ color: {TEXT}; }}
  .vc-card b.hl {{ color: {NEON_ICE}; }}

  /* --- Catatan / peringatan --- */
  .vc-note {{
      background: rgba(0,207,193,0.07);
      border-left: 3px solid {TURQUOISE};
      border-radius: 8px;
      padding: .85rem 1.1rem;
      color: {TEXT_MUTED};
      font-size: .88rem;
      line-height: 1.6;
      margin: .6rem 0 1rem 0;
  }}
  .vc-warn {{
      background: rgba(175,56,0,0.12);
      border-left: 3px solid {FLAME};
      border-radius: 8px;
      padding: .85rem 1.1rem;
      color: {TEXT_MUTED};
      font-size: .88rem;
      line-height: 1.6;
      margin: .6rem 0 1rem 0;
  }}
  .vc-note strong, .vc-warn strong {{ color: {TEXT}; }}

  /* --- Sidebar --- */
  section[data-testid="stSidebar"] {{
      background: {SURFACE};
      border-right: 1px solid {LINE};
  }}
  section[data-testid="stSidebar"] .block-container {{ padding-top: 1.5rem; }}

  /* --- Tab --- */
  .stTabs [data-baseweb="tab-list"] {{ gap: .3rem; border-bottom: 1px solid {LINE}; }}
  .stTabs [data-baseweb="tab"] {{
      color: {TEXT_MUTED};
      background: transparent;
      border-radius: 8px 8px 0 0;
      padding: .5rem 1rem;
  }}
  .stTabs [aria-selected="true"] {{ color: {TEXT}; background: {SURFACE_ALT}; }}

  /* --- Dataframe --- */
  [data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 10px; }}

  /* --- Divider --- */
  hr {{ border-color: {LINE}; }}
</style>
"""


def kpi(label: str, value: str, delta: str = "", variant: str = "", direction: str = "") -> str:
    """HTML kartu KPI. `variant` salah satu dari '', 'turq', 'ice', 'rust'."""
    delta_cls = f"vc-kpi-delta {direction}".strip()
    delta_html = f'<div class="{delta_cls}">{delta}</div>' if delta else ""
    return (
        f'<div class="vc-kpi {variant}">'
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
        f"<h4 style='margin:0'>{title}</h4>"
        f"<p>{body}</p>"
        f"</div>"
    )
