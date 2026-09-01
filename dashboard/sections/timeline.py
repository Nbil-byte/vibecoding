"""Halaman timeline: volume, kurva adopsi, dan deteksi lonjakan."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from .. import data as D
from ..theme import CERULEAN, DARK_SLATE, GOLDENROD, NEGATIVE, TUSCAN, BORDER, kpi


def _daily_chart(df, spikes):
    g = D.daily_volume(df)

    fig = go.Figure()
    fig.add_bar(
        x=g["date"], y=g["posts"], name="post harian",
        marker=dict(color="rgba(67,124,144,0.25)"), hovertemplate="%{x|%d %b %Y}<br>%{y} post<extra></extra>",
    )
    fig.add_scatter(
        x=g["date"], y=g["ma7"], name="rata-rata 7 hari",
        mode="lines", line=dict(color=CERULEAN, width=2.2),
        hovertemplate="%{x|%d %b %Y}<br>MA7 %{y:.1f}<extra></extra>",
    )
    if len(spikes):
        fig.add_scatter(
            x=spikes["date"], y=spikes["posts"], name="lonjakan (z ≥ 2,5)",
            mode="markers",
            marker=dict(
                size=11, color=TUSCAN, symbol="diamond",
                line=dict(color="#FFFFFF", width=1.5),
            ),
            hovertemplate="%{x|%d %b %Y}<br><b>%{y} post</b><br>lonjakan<extra></extra>",
        )
    fig.update_layout(
        title="Volume harian dan lonjakan terdeteksi",
        height=420, yaxis_title="post per hari",
        legend=dict(orientation="h", y=1.12, x=0),
    )
    return fig


def _adoption_chart(df):
    qv = D.quarter_volume(df)

    fig = go.Figure()
    fig.add_scatter(
        x=qv["quarter"], y=qv["cumulative"], name="kumulatif",
        mode="lines", fill="tozeroy", line=dict(color=DARK_SLATE, width=2.5, shape="spline"),
        fillcolor="rgba(37,89,87,0.10)",
        hovertemplate="%{x}<br>kumulatif %{y}<extra></extra>",
    )
    fig.update_layout(
        title="Kurva adopsi kumulatif",
        height=340, yaxis_title="total post (kumulatif)",
    )
    return fig


def _growth_chart(df):
    qv = D.quarter_volume(df)
    qv = qv[qv["posts"] >= D.MIN_QUARTER_DOCS].dropna(subset=["growth_%"])

    colors = [CERULEAN if v >= 0 else NEGATIVE for v in qv["growth_%"]]
    fig = go.Figure()
    fig.add_bar(
        x=qv["quarter"], y=qv["growth_%"], marker=dict(color=colors),
        hovertemplate="%{x}<br>%{y:+.1f}%<extra></extra>",
    )
    fig.add_hline(y=0, line=dict(color="rgba(37,89,87,0.12)", width=1))
    fig.update_layout(
        title="Pertumbuhan volume antar kuartal (%)",
        height=340, yaxis_title="perubahan (%)", showlegend=False,
    )
    return fig


def render(df, sent, topics):
    st.header("Timeline percakapan")
    st.caption(
        "Bersumber dari `timeline_analysis.ipynb`: tren volume, kurva adopsi, "
        "dan deteksi lonjakan harian sebagai kandidat event."
    )

    spikes = D.detect_spikes(df)
    daily = D.daily_volume(df)
    qv = D.quarter_volume(df)

    busiest = daily.loc[daily["posts"].idxmax()]
    active_days = int((daily["posts"] > 0).sum())

    c = st.columns(4)
    c[0].markdown(
        kpi("Rentang data", f"{len(daily)} hari",
            f"{active_days} hari ada aktivitas"), unsafe_allow_html=True)
    c[1].markdown(
        kpi("Hari tersibuk", f"{busiest['posts']:.0f} post",
            f"{busiest['date']:%d %b %Y}", variant="tuscan"), unsafe_allow_html=True)
    c[2].markdown(
        kpi("Lonjakan terdeteksi", str(len(spikes)),
            "z ≥ 2,5 vs baseline 28 hari", variant="cerulean"), unsafe_allow_html=True)
    c[3].markdown(
        kpi("Median harian", f"{daily['posts'].median():.0f} post",
            f"puncak kuartal {qv.loc[qv['posts'].idxmax(), 'quarter']}"),
        unsafe_allow_html=True)

    st.markdown("")
    st.plotly_chart(_daily_chart(df, spikes), use_container_width=True)

    st.markdown(
        """<div class="vc-note">
        <strong>Kenapa baseline bergerak, bukan rata-rata global.</strong>
        Volume dasar naik drastis sepanjang periode. Bila lonjakan diukur terhadap
        rata-rata seluruh rentang, hampir setiap hari di masa akhir akan tampak
        sebagai "lonjakan" — padahal itu sekadar pertumbuhan normal. Karena itu
        z-score dihitung terhadap rata-rata bergerak 28 hari, sehingga yang
        tertangkap adalah anomali <em>relatif terhadap kondisi saat itu</em>.
        </div>""",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    left.plotly_chart(_adoption_chart(df), use_container_width=True)
    right.plotly_chart(_growth_chart(df), use_container_width=True)

    # --- Tabel lonjakan + contoh post ---
    st.subheader("Lonjakan teratas")
    if not len(spikes):
        st.markdown(
            '<div class="vc-warn">Tidak ada lonjakan melewati ambang. '
            "Turunkan <code>z_threshold</code> pada <code>detect_spikes()</code> "
            "bila ingin deteksi lebih sensitif.</div>",
            unsafe_allow_html=True,
        )
        return

    show = spikes.head(10)[["date", "posts", "baseline", "z"]].copy()
    show["date"] = show["date"].dt.strftime("%d %b %Y")
    show = show.rename(columns={
        "date": "Tanggal", "posts": "Post", "baseline": "Baseline", "z": "z-score",
    })
    st.dataframe(
        show.style.format({"Baseline": "{:.1f}", "z-score": "{:.2f}"}),
        use_container_width=True, hide_index=True,
    )

    st.subheader("Apa yang terjadi pada hari lonjakan")
    st.caption("Post dengan engagement tertinggi pada tanggal terpilih.")

    options = spikes.head(10)["date"].dt.strftime("%d %b %Y").tolist()
    pick = st.selectbox("Pilih tanggal lonjakan", options, label_visibility="collapsed")
    chosen = spikes.head(10).iloc[options.index(pick)]["date"]

    ex = D.spike_examples(df, chosen, n=5)
    if not len(ex):
        st.info("Tidak ada post pada tanggal itu.")
        return

    for row in ex.itertuples():
        user = getattr(row, "username", "?")
        eng = getattr(row, "engagement", 0)
        url = getattr(row, "post_url", "")
        link = f' · <a href="{url}" target="_blank" style="color:{CERULEAN}">buka</a>' if isinstance(url, str) and url.startswith("http") else ""
        st.markdown(
            f"""<div class="vc-card" style="padding:.9rem 1.1rem">
            <div style="color:{CERULEAN};font-size:.8rem;font-weight:600">
              @{user} · engagement {int(eng)}{link}
            </div>
            <p style="margin-top:.4rem">{str(row.text)[:400]}</p>
            </div>""",
            unsafe_allow_html=True,
        )
