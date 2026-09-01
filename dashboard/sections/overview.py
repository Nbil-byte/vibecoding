"""Halaman narasi: perkembangan vibe coding sebagai cerita berbasis data."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from .. import data as D
from .. import narrative as N
from ..theme import (
    CERULEAN,
    DARK_SLATE,
    GOLDENROD,
    NEGATIVE,
    TUSCAN,
    BORDER,
    era_card,
    kpi,
)


def _volume_story(df, sent):
    """Grafik volume kuartalan dengan penanda puncak dan overlay net sentiment."""
    qv = D.quarter_volume(df)
    valid = qv[qv["posts"] >= D.MIN_QUARTER_DOCS]
    sparse = qv[qv["posts"] < D.MIN_QUARTER_DOCS]

    fig = go.Figure()

    # Kuartal bervolume mikro digambar terpisah dengan warna redam,
    # supaya terlihat ada tapi jelas tidak dipakai untuk tren.
    if len(sparse):
        fig.add_bar(
            x=sparse["quarter"],
            y=sparse["posts"],
            name=f"< {D.MIN_QUARTER_DOCS} post (dikecualikan)",
            marker=dict(color=BORDER, line=dict(color=GOLDENROD, width=1)),
            hovertemplate="%{x}<br>%{y} post<br><i>dikecualikan dari tren</i><extra></extra>",
        )

    fig.add_bar(
        x=valid["quarter"],
        y=valid["posts"],
        name="Volume post",
        marker=dict(
            color=valid["posts"],
            colorscale=[[0, "#6B9AAB"], [0.5, CERULEAN], [1, DARK_SLATE]],
            line=dict(width=0),
        ),
        hovertemplate="%{x}<br><b>%{y} post</b><extra></extra>",
    )

    if len(sent):
        sq = D.sentiment_by_quarter(sent)
        if len(sq):
            fig.add_scatter(
                x=sq["quarter"],
                y=sq["net"],
                name="Net sentiment (pp)",
                yaxis="y2",
                mode="lines+markers",
                line=dict(color=TUSCAN, width=2.5, shape="spline"),
                marker=dict(size=7, color=TUSCAN, line=dict(color="#FFFFFF", width=1.5)),
                hovertemplate="%{x}<br>net %{y:+.1f} pp<extra></extra>",
            )
            fig.update_layout(
                yaxis2=dict(
                    overlaying="y",
                    side="right",
                    title="net sentiment (pp)",
                    gridcolor="rgba(0,0,0,0)",
                    zeroline=True,
                    zerolinecolor="rgba(37,89,87,0.12)",
                    tickfont=dict(color=TUSCAN),
                )
            )

    if len(qv):
        peak = qv.loc[qv["posts"].idxmax()]
        fig.add_annotation(
            x=peak["quarter"],
            y=peak["posts"],
            text=f"puncak · {int(peak['posts'])}",
            showarrow=True,
            arrowhead=0,
            arrowcolor=TUSCAN,
            ax=0,
            ay=-32,
            font=dict(color=TUSCAN, size=11),
        )

    fig.update_layout(
        title="Volume percakapan per kuartal",
        height=420,
        barmode="overlay",
        legend=dict(orientation="h", y=1.12, x=0),
        yaxis_title="jumlah post",
    )
    return fig


def render(df, sent, topics):
    stats = N.headline_stats(df, sent)

    st.markdown(
        f"""
        <div class="vc-hero">
          <span class="vc-badge">{stats['start']:%b %Y} – {stats['end']:%b %Y}</span>
          <span class="vc-badge accent">{N._fmt(stats['total'])} post</span>
          <div class="vc-hero-title">Dari Meme ke Metodologi</div>
          <p class="vc-hero-sub">
            Bagaimana <strong>vibe coding</strong> berpindah dari lelucon di timeline
            menjadi cara kerja yang diperdebatkan secara serius — dilacak lewat
            {N._fmt(stats['total'])} post X/Twitter.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- KPI ---
    c = st.columns(4)
    c[0].markdown(
        kpi("Total post", N._fmt(stats["total"]),
            f"{stats['quarters_valid']} dari {stats['quarters_total']} kuartal layak tren"),
        unsafe_allow_html=True,
    )
    c[1].markdown(
        kpi("Kuartal puncak", str(stats["peak_quarter"]),
            f"{N._fmt(stats['peak_posts'])} post",
            variant="tuscan", direction="up"),
        unsafe_allow_html=True,
    )
    growth = (
        f"{stats['growth_multiple']:.0f}×"
        if stats["growth_multiple"] == stats["growth_multiple"]
        else "—"
    )
    c[2].markdown(
        kpi("Pertumbuhan puncak", growth,
            f"sejak {stats['first_valid_quarter']}", variant="cerulean", direction="up"),
        unsafe_allow_html=True,
    )
    if len(sent):
        arah = "up" if stats["net"] >= 0 else "down"
        c[3].markdown(
            kpi("Net sentiment", f"{stats['net']:+.1f}",
                f"dari {N._fmt(len(sent))} post berlabel",
                variant="cerulean" if stats["net"] >= 0 else "negative", direction=arah),
            unsafe_allow_html=True,
        )
    else:
        c[3].markdown(
            kpi("Net sentiment", "—", "belum ada data berlabel", variant="negative"),
            unsafe_allow_html=True,
        )

    st.markdown("")
    st.plotly_chart(_volume_story(df, sent), use_container_width=True)

    # --- Metodologi pengumpulan data ---
    st.markdown(
        """<div class="vc-callout method">
        <div class="vc-callout-title">Bagaimana data dikumpulkan</div>
        <p>Data dikumpulkan dari halaman pencarian X/Twitter memakai dua scraper:
        <strong>Playwright</strong> (browser automation) dan <strong>twscrape</strong>
        (API wrapper). Query utama yang dipakai:</p>
        <p style="font-family:monospace;font-size:.8rem;background:rgba(169,135,67,0.10);
        padding:.6rem .8rem;border-radius:6px;margin:.5rem 0">
        (vibecoding OR "vibe coding" OR "vibe-coding" OR "vibe coded"<br>
        OR "vibecode" OR "vibe coder" OR "ngoding pakai AI"<br>
        OR "kode pakai AI")
        </p>
        <p>Playwright menjalankan <strong>10 variasi query</strong> untuk memperluas
        cakupan, antara lain memfilter berdasarkan konteks
        (<code>app OR website OR project OR startup</code>),
        teknologi (<code>ai OR llm OR agent OR prompt</code>),
        tool (<code>cursor OR windsurf OR copilot OR claude OR replit OR lovable OR bolt</code>),
        aktivitas (<code>bug OR debug OR ship OR build OR github OR repo</code>),
        dan bahasa (<code>lang:en</code>, <code>lang:id</code>).
        twscrape memakai query tambahan <code>"AI coding"</code> dan
        <code>"coding pakai AI"</code>.</p>
        <p>Pencarian dijalankan dalam <strong>jendela tanggal 7 hari</strong> yang
        bergeser maju, memakai filter <em>live (chronological)</em> agar post
        diurutkan berdasarkan waktu. Duplikat dibuang setelah pengumpulan, dan
        post disaring ulang dengan daftar 14 kata kunci relevan (termasuk varian
        seperti <em>vibe-code</em>, <em>vibe-coded</em>, <em>vibe coders</em>,
        <em>ngoding pakai AI</em>) untuk membuang hasil yang tidak terkait.</p>
        </div>""",
        unsafe_allow_html=True,
    )

    # --- Narasi era ---
    st.subheader("Perjalanan dalam empat fase")
    st.caption(
        "Era dibagi adaptif dari sebaran volume aktual, bukan dari tanggal tetap. "
        "Seluruh angka dihitung ulang saat dashboard dimuat."
    )

    eras = N.build_eras(df, sent)
    cols = st.columns(2)
    for i, era in enumerate(eras):
        with cols[i % 2]:
            st.markdown(
                era_card(era["tag"], era["color"], era["title"], era["body"]),
                unsafe_allow_html=True,
            )

    st.markdown(
        f"""<div class="vc-callout info">
        <div class="vc-callout-title">Konteks eksternal</div>
        <p>Istilah <em>vibe coding</em> dipopulerkan Andrej Karpathy pada Februari 2025
        dan menyebar cepat sesudahnya. Konteks ini berasal dari pengetahuan umum,
        <strong>bukan</strong> dari dataset ini — dataset hanya dapat menunjukkan
        <em>kapan dan bagaimana</em> percakapan bergerak, bukan siapa yang memulainya.
        Sebaran data yang menipis sebelum 2025 konsisten dengan penanggalan tersebut.</p>
        </div>""",
        unsafe_allow_html=True,
    )

    # --- Temuan utama ---
    st.subheader("Temuan utama")
    for finding in N.key_findings(df, sent, stats):
        st.markdown(f"- {finding}")

    # --- Keterbatasan ---
    st.subheader("Yang tidak bisa disimpulkan dari data ini")
    st.markdown(
        """
- **Bukan sensus.** Data hanya dari X, dan hanya post yang tampil lewat halaman
  search. Percakapan di Reddit, HN, YouTube, atau grup tertutup tidak terwakili.
- **Volume bukan sentimen.** Naiknya jumlah post tidak berarti naiknya penerimaan.
  Kritik dan pujian sama-sama menambah volume.
- **Penyebutan tool bukan pangsa pasar.** Regex hanya menghitung siapa yang
  *dibicarakan*, bukan siapa yang *dipakai*. Tool dengan komunitas vokal akan
  tampak lebih besar daripada porsi pemakaian sebenarnya.
- **Korelasi bukan sebab.** Turunnya net sentiment berbarengan dengan naiknya
  volume tidak membuktikan salah satu menyebabkan yang lain.
        """
    )
