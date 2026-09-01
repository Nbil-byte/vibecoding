"""Halaman sentimen: distribusi, tren kuartalan, dan perbandingan antar tool."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from .. import data as D
from ..narrative import _fmt, _pct
from ..theme import (
    BORDER,
    CERULEAN,
    GOLDENROD,
    NEGATIVE,
    SENTIMENT_COLORS,
    SENTIMENT_ORDER,
    SURFACE_STRONG,
    TUSCAN,
    kpi,
)

LABEL_ID = {"negative": "Negatif", "neutral": "Netral", "positive": "Positif"}


def _donut(sent):
    vc = sent["sentiment"].value_counts()
    order = [s for s in SENTIMENT_ORDER if s in vc.index]

    fig = go.Figure(
        go.Pie(
            labels=[LABEL_ID[s] for s in order],
            values=[vc[s] for s in order],
            hole=0.62,
            marker=dict(
                colors=[SENTIMENT_COLORS[s] for s in order],
                line=dict(color=SURFACE_STRONG, width=2),
            ),
            textinfo="percent",
            textfont=dict(size=13),
            hovertemplate="%{label}<br>%{value} post (%{percent})<extra></extra>",
        )
    )
    net = (
        vc.get("positive", 0) - vc.get("negative", 0)
    ) / vc.sum() * 100
    fig.add_annotation(
        text=f"<b>{net:+.1f}</b><br><span style='font-size:11px'>net</span>",
        showarrow=False,
        font=dict(size=22, color=TUSCAN if net >= 0 else NEGATIVE),
    )
    fig.update_layout(title="Distribusi sentimen", height=340, showlegend=True)
    return fig


def _quarter_chart(sq):
    fig = go.Figure()
    for s in SENTIMENT_ORDER:
        if s in sq.columns:
            fig.add_bar(
                x=sq["quarter"], y=sq[s], name=LABEL_ID[s],
                marker=dict(color=SENTIMENT_COLORS[s], line=dict(width=0)),
                hovertemplate="%{x}<br>" + LABEL_ID[s] + " %{y:.1f}%<extra></extra>",
            )
    fig.add_scatter(
        x=sq["quarter"], y=sq["net"], name="Net", yaxis="y2", mode="lines+markers",
        line=dict(color=TUSCAN, width=2.5, shape="spline"),
        marker=dict(size=7, color=TUSCAN, line=dict(color=SURFACE_STRONG, width=1.5)),
        hovertemplate="%{x}<br>net %{y:+.1f} pp<extra></extra>",
    )
    fig.update_layout(
        title="Komposisi sentimen per kuartal (%)",
        barmode="stack", height=420, yaxis_title="pangsa (%)",
        yaxis2=dict(
            overlaying="y", side="right", title="net (pp)",
            gridcolor="rgba(0,0,0,0)", zeroline=True, zerolinecolor="rgba(37,89,87,0.12)",
            tickfont=dict(color=TUSCAN),
        ),
        legend=dict(orientation="h", y=1.12, x=0),
    )
    return fig


def _tool_chart(st_tool):
    colors = [CERULEAN if v >= 0 else NEGATIVE for v in st_tool["net"]]
    fig = go.Figure()
    fig.add_bar(
        x=st_tool["net"], y=st_tool["tool"], orientation="h",
        marker=dict(color=colors),
        text=[f"{v:+.1f}" for v in st_tool["net"]],
        textposition="outside", textfont=dict(size=11),
        customdata=st_tool[["n", "positive", "negative"]].values,
        hovertemplate=(
            "<b>%{y}</b><br>net %{x:+.1f} pp<br>"
            "n = %{customdata[0]}<br>positif %{customdata[1]:.1f}% · "
            "negatif %{customdata[2]:.1f}%<extra></extra>"
        ),
    )
    fig.add_vline(x=0, line=dict(color="rgba(37,89,87,0.12)", width=1))
    fig.update_layout(
        title="Net sentiment per tool (positif − negatif, poin persen)",
        height=max(320, 34 * len(st_tool)), showlegend=False,
        xaxis_title="net sentiment (pp)",
        yaxis=dict(autorange="reversed"),
    )
    return fig


def _volume_vs_net(st_tool):
    fig = go.Figure()
    fig.add_scatter(
        x=st_tool["n"], y=st_tool["net"], mode="markers+text",
        text=st_tool["tool"], textposition="top center",
        textfont=dict(size=10, color=GOLDENROD),
        marker=dict(
            size=st_tool["n"] / st_tool["n"].max() * 38 + 12,
            color=st_tool["net"],
            colorscale=[[0, NEGATIVE], [0.5, GOLDENROD], [1, CERULEAN]],
            line=dict(color=SURFACE_STRONG, width=1.5),
        ),
        hovertemplate="<b>%{text}</b><br>n = %{x}<br>net %{y:+.1f} pp<extra></extra>",
    )
    fig.add_hline(y=0, line=dict(color="rgba(37,89,87,0.12)", width=1, dash="dot"))
    fig.update_layout(
        title="Volume pembicaraan vs net sentiment",
        height=400, xaxis_title="jumlah penyebutan", yaxis_title="net sentiment (pp)",
        showlegend=False,
    )
    return fig


def render(df, sent, topics):
    st.header("Analisis sentimen")
    st.caption(
        "Bersumber dari `sentiment_colab.ipynb`. Model: "
        "`cardiffnlp/twitter-xlm-roberta-base-sentiment` — multilingual, "
        "dilatih pada teks Twitter."
    )

    if not len(sent):
        st.markdown(
            """<div class="vc-warn">
            <strong>Belum ada data berlabel sentimen.</strong> Dashboard mencari file
            berpola <code>*sentimen*.csv</code> di <code>data/raw/</code> atau
            <code>data/processed/</code>.<br><br>
            Hasilkan dengan menjalankan <code>python label_sentimen.py 0 10000</code>,
            atau jalankan <code>sentiment_colab.ipynb</code> lalu simpan hasilnya ke
            <code>data/processed/</code>.
            </div>""",
            unsafe_allow_html=True,
        )
        return

    coverage = len(sent) / len(df) * 100
    vc = sent["sentiment"].value_counts(normalize=True).mul(100)
    low_conf = (sent["sentiment_score"] < 0.5).mean() * 100 if "sentiment_score" in sent else float("nan")

    c = st.columns(4)
    c[0].markdown(
        kpi("Post berlabel", _fmt(len(sent)),
            f"{_pct(coverage)} dari {_fmt(len(df))} total"), unsafe_allow_html=True)
    c[1].markdown(
        kpi("Positif", _pct(vc.get("positive", 0)), variant="cerulean", direction="up"),
        unsafe_allow_html=True)
    c[2].markdown(
        kpi("Negatif", _pct(vc.get("negative", 0)), variant="negative", direction="down"),
        unsafe_allow_html=True)
    c[3].markdown(
        kpi("Keyakinan < 0,50",
            _pct(low_conf) if low_conf == low_conf else "—",
            "perlu tinjauan manual", variant="tuscan"), unsafe_allow_html=True)

    if coverage < 95:
        sent_span = f"{sent['created_dt'].min():%b %Y} – {sent['created_dt'].max():%b %Y}"
        full_span = f"{df['created_dt'].min():%b %Y} – {df['created_dt'].max():%b %Y}"
        st.markdown(
            f"""<div class="vc-warn">
            <strong>Cakupan label baru {_pct(coverage)}</strong>
            ({_fmt(len(sent))} dari {_fmt(len(df))} post), dan subset itu
            <strong>bukan sampel acak</strong>.
            <br><br>
            Post berlabel hanya mencakup <b>{sent_span}</b>, sementara dataset penuh
            membentang <b>{full_span}</b>. Pelabelan dijalankan atas potongan baris
            berurutan, dan karena file tersimpan terurut waktu, subsetnya terkonsentrasi
            pada periode terbaru saja.
            <br><br>
            Akibatnya, angka pada halaman ini <strong>tidak dapat digeneralisasi</strong>
            ke keseluruhan korpus — periode awal sama sekali tidak terwakili. Labeli
            seluruh dataset lebih dulu sebelum menarik kesimpulan kuantitatif:
            <code>python label_sentimen.py 0 10000</code>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("")
    left, right = st.columns([1, 1.6])
    left.plotly_chart(_donut(sent), use_container_width=True)

    sq = D.sentiment_by_quarter(sent)
    if len(sq) >= 2:
        right.plotly_chart(_quarter_chart(sq), use_container_width=True)
    else:
        right.markdown(
            '<div class="vc-warn">Kuartal bervolume memadai belum cukup '
            "untuk grafik tren.</div>", unsafe_allow_html=True)

    # --- Per tool ---
    st.subheader("Sentimen per tool")
    sent_tagged = D.tag_tools(sent)
    st_tool = D.sentiment_by_tool(sent_tagged)

    if not len(st_tool):
        st.markdown(
            '<div class="vc-warn">Tidak ada tool dengan penyebutan mencukupi '
            "(minimum 10) pada subset berlabel.</div>", unsafe_allow_html=True)
    else:
        a, b = st.columns([1.15, 1])
        a.plotly_chart(_tool_chart(st_tool), use_container_width=True)
        b.plotly_chart(_volume_vs_net(st_tool), use_container_width=True)

        if len(st_tool) >= 5:
            corr = st_tool["n"].corr(st_tool["net"])
            if corr == corr:
                arah = "negatif" if corr < 0 else "positif"
                tafsir = (
                    "tool yang paling banyak dibicarakan justru cenderung paling "
                    "banyak dikeluhkan — pola yang wajar bila pemakaian intensif "
                    "memunculkan lebih banyak friksi nyata"
                    if corr < -0.3
                    else "hubungan antara volume dan sentimen tergolong lemah"
                )
                st.markdown(
                    f"""<div class="vc-note">
                    Korelasi volume penyebutan terhadap net sentiment:
                    <strong>r = {corr:.2f}</strong> ({arah}). Artinya {tafsir}.
                    Korelasi <strong>bukan sebab-akibat</strong>, dan dengan
                    {len(st_tool)} titik data saja angka ini rapuh.
                    </div>""",
                    unsafe_allow_html=True,
                )

        st.dataframe(
            st_tool.rename(columns={
                "tool": "Tool", "n": "Penyebutan", "positive": "Positif %",
                "neutral": "Netral %", "negative": "Negatif %", "net": "Net (pp)",
            }),
            use_container_width=True, hide_index=True,
        )

    # --- Contoh post ---
    st.subheader("Contoh post per sentimen")
    pick = st.radio(
        "Sentimen", SENTIMENT_ORDER, horizontal=True,
        format_func=lambda s: LABEL_ID[s], label_visibility="collapsed",
    )
    sub = sent[sent["sentiment"] == pick]
    if "sentiment_score" in sub.columns:
        sub = sub.nlargest(4, "sentiment_score")
    else:
        sub = sub.head(4)

    for row in sub.itertuples():
        score = getattr(row, "sentiment_score", None)
        badge = f" · keyakinan {score:.2f}" if score is not None else ""
        st.markdown(
            f"""<div class="vc-card" style="padding:.9rem 1.1rem;
                 border-left:3px solid {SENTIMENT_COLORS[pick]}">
            <div style="color:{SENTIMENT_COLORS[pick]};font-size:.8rem;font-weight:600">
              @{getattr(row, 'username', '?')}{badge}
            </div>
            <p style="margin-top:.4rem">{str(row.text)[:400]}</p>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown(
        """<div class="vc-note">
        <strong>Keterbatasan model.</strong> Ironi dan sarkasme tetap sulit —
        kalimat seperti <em>"vibe coding is amazing until production crashes"</em>
        sering terklasifikasi kurang tepat. Teks juga dipotong pada 128 token,
        sehingga tweet panjang kehilangan sebagian konteks.
        </div>""",
        unsafe_allow_html=True,
    )
