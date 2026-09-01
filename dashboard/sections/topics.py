"""Halaman topik: artefak BERTopic bila tersedia, plus analisis tool dan istilah."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from .. import data as D
from ..narrative import _fmt, _pct
from ..theme import (
    CATEGORICAL,
    CERULEAN,
    DARK_SLATE,
    GOLDENROD,
    HEAT_SCALE,
    NEGATIVE,
    SURFACE_STRONG,
    TUSCAN,
    kpi,
)


def _tool_share_chart(tsq, tools):
    fig = go.Figure()
    for i, tool in enumerate(tools):
        sub = tsq[tsq["tool"] == tool].sort_values("quarter")
        fig.add_scatter(
            x=sub["quarter"], y=sub["share"], name=tool,
            mode="lines+markers", stackgroup="one",
            line=dict(width=0.5, color=CATEGORICAL[i % len(CATEGORICAL)]),
            fillcolor=CATEGORICAL[i % len(CATEGORICAL)],
            hovertemplate="%{x}<br>" + tool + " %{y:.1f}%<extra></extra>",
        )
    fig.update_layout(
        title="Pangsa penyebutan tool per kuartal (%)",
        height=420, yaxis_title="pangsa dari post bertool (%)",
        legend=dict(orientation="h", y=-0.18, x=0),
    )
    return fig


def _tool_heatmap(tsq, tools):
    piv = (
        tsq[tsq["tool"].isin(tools)]
        .pivot(index="tool", columns="quarter", values="share")
        .reindex(tools)
    )
    fig = go.Figure(
        go.Heatmap(
            z=piv.values, x=piv.columns, y=piv.index,
            colorscale=HEAT_SCALE, hoverongaps=False,
            hovertemplate="%{y} · %{x}<br>%{z:.1f}%<extra></extra>",
            colorbar=dict(title="pangsa %", outlinewidth=0),
        )
    )
    fig.update_layout(title="Heatmap evolusi penyebutan tool", height=380)
    return fig


def _terms_chart(terms):
    fig = go.Figure()
    fig.add_bar(
        x=terms["count"], y=terms["term"], orientation="h",
        marker=dict(
            color=terms["count"],
            colorscale=[[0, GOLDENROD], [0.5, CERULEAN], [1, DARK_SLATE]],
        ),
        hovertemplate="<b>%{y}</b><br>%{x} kemunculan<extra></extra>",
    )
    fig.update_layout(
        title="Istilah paling sering muncul",
        height=max(340, 22 * len(terms)), showlegend=False,
        yaxis=dict(autorange="reversed"), xaxis_title="kemunculan",
    )
    return fig


def _render_bertopic(topics):
    """Tampilkan artefak BERTopic bila file CSV-nya tersedia."""
    summary = topics.get("summary")
    diag = topics.get("diagnostics")
    quarter = topics.get("quarter")

    st.subheader("Hasil BERTopic")

    if summary is not None and len(summary):
        n_topics = len(summary[summary.get("Topic", -1) != -1]) if "Topic" in summary else len(summary)
        flagged = 0
        if diag is not None and "flag" in diag.columns:
            flagged = int((diag["flag"] != "ok").sum())

        c = st.columns(3)
        c[0].markdown(kpi("Topik ditemukan", str(n_topics)), unsafe_allow_html=True)
        c[1].markdown(
            kpi("Ditandai meragukan", str(flagged),
                "tidak koheren atau catch-all", variant="negative"), unsafe_allow_html=True)
        if diag is not None and "coherence" in diag.columns:
            c[2].markdown(
                kpi("Koherensi median", f"{diag['coherence'].median():.3f}",
                    "cosine ke centroid", variant="cerulean"), unsafe_allow_html=True)

        st.dataframe(summary, use_container_width=True, hide_index=True)

    if diag is not None and len(diag) and {"coherence", "n"} <= set(diag.columns):
        colors = [
            NEGATIVE if (f != "ok") else CERULEAN
            for f in diag.get("flag", ["ok"] * len(diag))
        ]
        fig = go.Figure()
        fig.add_scatter(
            x=diag["coherence"], y=diag["n"], mode="markers+text",
            text=diag["topic"] if "topic" in diag.columns else None,
            textposition="middle center", textfont=dict(size=9, color=SURFACE_STRONG),
            marker=dict(size=26, color=colors, line=dict(color=SURFACE_STRONG, width=1.5)),
            hovertemplate="topik %{text}<br>koherensi %{x:.3f}<br>n = %{y}<extra></extra>",
        )
        fig.update_layout(
            title="Koherensi vs ukuran topik (merah = ditandai meragukan)",
            height=400, xaxis_title="koherensi", yaxis_title="jumlah dokumen",
            yaxis_type="log", showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(
            """<div class="vc-note">
            <strong>Kuadran kanan-bawah adalah yang sehat</strong> — topik koheren
            berukuran wajar. Titik di kiri (koherensi rendah) berarti anggota topik
            tidak saling mirip; kata kuncinya bisa tetap tampak meyakinkan meski
            dokumennya tak berhubungan. Titik sangat tinggi di sumbu Y menandakan
            topik <em>catch-all</em> yang terlalu luas untuk bermakna.
            </div>""",
            unsafe_allow_html=True,
        )

    if quarter is not None and len(quarter):
        st.subheader("Pangsa topik per kuartal")
        st.dataframe(quarter, use_container_width=True)


def render(df, sent, topics):
    st.header("Topik dan tool")
    st.caption(
        "Bersumber dari `topic_modeling.ipynb`: BERTopic dengan embedding "
        "multilingual, UMAP, HDBSCAN, dan c-TF-IDF."
    )

    if topics:
        _render_bertopic(topics)
        st.divider()
    else:
        st.markdown(
            """<div class="vc-warn">
            <strong>Artefak BERTopic belum tersedia.</strong> Dashboard mencari
            <code>vibecoding_topics_summary.csv</code>,
            <code>vibecoding_topics_diagnostics.csv</code>, dan
            <code>vibecoding_topics_per_quarter.csv</code> di root repo atau
            <code>data/processed/</code>.<br><br>
            Jalankan <code>topic_modeling.ipynb</code> sampai sel "Simpan Hasil".
            Bila dijalankan di Colab, unduh CSV keluarannya lalu letakkan di
            <code>data/processed/</code>.<br><br>
            <strong>Topic modeling sengaja tidak dijalankan di dalam dashboard</strong> —
            embedding 10rb dokumen plus UMAP dan HDBSCAN terlalu berat untuk
            dieksekusi pada setiap muat halaman, dan hasilnya tidak deterministik
            antar sesi.
            </div>""",
            unsafe_allow_html=True,
        )

    # --- Analisis tool: selalu tersedia karena dihitung dari teks ---
    st.subheader("Penyebutan tool sepanjang waktu")
    st.caption(
        "Dihitung langsung dari teks memakai pencocokan regex, sehingga tidak "
        "bergantung pada artefak BERTopic."
    )

    counts = D.tool_counts(df)
    counts = counts[counts["mentions"] > 0]

    if not len(counts):
        st.info("Tidak ada penyebutan tool terdeteksi.")
        return

    c = st.columns(4)
    total_tool = int(df["tool_any"].sum())
    c[0].markdown(
        kpi("Post menyebut tool", _fmt(total_tool),
            f"{_pct(total_tool / len(df) * 100)} dari total"), unsafe_allow_html=True)
    c[1].markdown(
        kpi("Tool terdeteksi", str(len(counts)), variant="cerulean"), unsafe_allow_html=True)
    c[2].markdown(
        kpi("Paling banyak dibahas", counts.iloc[0]["tool"],
            f"{_fmt(counts.iloc[0]['mentions'])} penyebutan", variant="tuscan"),
        unsafe_allow_html=True)
    c[3].markdown(
        kpi("Konsentrasi 3 teratas",
            _pct(counts.head(3)["mentions"].sum() / counts["mentions"].sum() * 100)),
        unsafe_allow_html=True)

    st.markdown("")

    max_tools = min(8, len(counts))
    n_tools = st.slider("Jumlah tool ditampilkan", 3, max_tools, max_tools) if max_tools > 3 else max_tools
    tools = counts.head(n_tools)["tool"].tolist()

    tsq = D.tool_share_by_quarter(df)
    if len(tsq):
        st.plotly_chart(_tool_share_chart(tsq, tools), use_container_width=True)
        st.plotly_chart(_tool_heatmap(tsq, tools), use_container_width=True)

        st.markdown(
            """<div class="vc-warn">
            <strong>Penyebutan bukan pangsa pasar.</strong> Angka ini menghitung
            siapa yang <em>dibicarakan</em> di X, bukan siapa yang <em>dipakai</em>.
            Tool dengan komunitas vokal atau kontroversi aktif akan tampak jauh
            lebih besar daripada porsi pemakaian sebenarnya. Pencocokan regex juga
            bisa salah tangkap pada kata ambigu seperti <code>bolt</code> atau
            <code>cursor</code> dalam konteks non-tool.
            </div>""",
            unsafe_allow_html=True,
        )

    # --- Istilah teratas ---
    st.subheader("Istilah dominan")
    left, right = st.columns([1, 1])

    quarters = D.valid_quarters(df)
    scope = left.selectbox(
        "Periode", ["Seluruh periode"] + quarters, index=0,
    )
    sub = df if scope == "Seluruh periode" else df[df["quarter"] == scope]
    n_terms = right.slider("Jumlah istilah", 10, 40, 22)

    st.plotly_chart(_terms_chart(D.top_terms(sub, n=n_terms)), use_container_width=True)

    st.markdown(
        """<div class="vc-note">
        <strong>Ini bukan topic modeling.</strong> Grafik di atas hanya menghitung
        frekuensi kata setelah stopword dibuang — tidak ada pengelompokan semantik
        di dalamnya. Dua post yang membahas hal sama dengan kata berbeda tidak
        akan terhubung. Untuk pengelompokan semantik sesungguhnya, jalankan
        <code>topic_modeling.ipynb</code> dan muat artefaknya.
        </div>""",
        unsafe_allow_html=True,
    )
