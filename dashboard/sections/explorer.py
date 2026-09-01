"""Halaman penjelajah data: filter, pencarian, dan ekspor."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from .. import data as D
from ..narrative import _fmt, _pct
from ..theme import CERULEAN, DARK_SLATE, kpi


def render(df, sent, topics):
    st.header("Penjelajah data")
    st.caption(
        "Data mentah hasil scraping beserta label sentimen bila tersedia. "
        "Gunakan filter untuk memeriksa post secara langsung."
    )

    # --- Filter ---
    f = st.columns([1.2, 1.2, 1])
    quarters = sorted(df["quarter"].unique())
    q_pick = f[0].multiselect("Kuartal", quarters, default=[])

    tools_all = D.tool_counts(df)
    tools_all = tools_all[tools_all["mentions"] > 0]["tool"].tolist()
    t_pick = f[1].multiselect("Tool disebut", tools_all, default=[])

    has_sent = "sentiment" in df.columns
    s_pick = f[2].multiselect(
        "Sentimen", ["negative", "neutral", "positive"], default=[],
        disabled=not has_sent,
        help=None if has_sent else "Gabungkan data berlabel untuk mengaktifkan",
    )

    query = st.text_input("Cari dalam teks", placeholder="mis. production, refactor, bug")

    # --- Terapkan filter ---
    view = df.copy()
    if q_pick:
        view = view[view["quarter"].isin(q_pick)]
    if t_pick:
        mask = view[[f"tool_{t}" for t in t_pick]].any(axis=1)
        view = view[mask]
    if s_pick and has_sent:
        view = view[view["sentiment"].isin(s_pick)]
    if query.strip():
        view = view[
            view["text"].astype(str).str.contains(query.strip(), case=False, na=False)
        ]

    # --- Ringkasan ---
    c = st.columns(3)
    c[0].markdown(
        kpi("Post terfilter", _fmt(len(view)),
            f"{_pct(len(view) / len(df) * 100)} dari {_fmt(len(df))}"),
        unsafe_allow_html=True)
    c[1].markdown(
        kpi("Akun unik",
            _fmt(view["username"].nunique()) if "username" in view and len(view) else "—",
            variant="cerulean"), unsafe_allow_html=True)
    c[2].markdown(
        kpi("Rentang",
            f"{view['created_dt'].min():%b %Y} – {view['created_dt'].max():%b %Y}"
            if len(view) else "—", variant="tuscan"), unsafe_allow_html=True)

    if not len(view):
        st.markdown(
            '<div class="vc-warn">Tidak ada post yang cocok dengan filter. '
            "Longgarkan kriterianya.</div>", unsafe_allow_html=True)
        return

    st.markdown("")

    # --- Tabel ---
    cols = [c for c in (
        "created_dt", "username", "text",
        "like_count", "retweet_count", "reply_count", "sentiment", "sentiment_score",
    ) if c in view.columns]

    table = view[cols].sort_values("created_dt", ascending=False).head(500)

    st.subheader(f"Tabel post ({_fmt(min(len(view), 500))} teratas)")
    st.dataframe(
        table.rename(columns={
            "created_dt": "Waktu", "username": "Akun", "text": "Teks",
            "like_count": "Like",
            "retweet_count": "Repost", "reply_count": "Reply",
            "sentiment": "Sentimen", "sentiment_score": "Keyakinan",
        }),
        use_container_width=True, hide_index=True, height=460,
    )

    st.download_button(
        "Unduh hasil filter (CSV)",
        data=view[cols].to_csv(index=False).encode("utf-8-sig"),
        file_name="vibecoding_filtered.csv",
        mime="text/csv",
    )

    # --- Akun paling aktif ---
    if "username" in view.columns:
        st.subheader("Akun paling aktif")
        top = (
            view.groupby("username")
            .agg(post=("text", "size"))
            .sort_values("post", ascending=False)
            .head(15)
            .reset_index()
        )
        fig = go.Figure()
        fig.add_bar(
            x=top["post"], y=top["username"], orientation="h",
            marker=dict(color=DARK_SLATE),
            hovertemplate="<b>@%{y}</b><br>%{x} post<extra></extra>",
        )
        fig.update_layout(
            height=max(320, 24 * len(top)), showlegend=False,
            xaxis_title="jumlah post", yaxis=dict(autorange="reversed"),
            title="15 akun dengan post terbanyak (dalam filter aktif)",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            """<div class="vc-note">
            Akun bervolume sangat tinggi patut diperiksa: sebagian adalah bot,
            agregator berita, atau akun promosi. Post semacam itu menaikkan volume
            tanpa mencerminkan percakapan organik.
            </div>""",
            unsafe_allow_html=True,
        )
