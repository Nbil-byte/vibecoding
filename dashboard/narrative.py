"""Penyusun narasi perkembangan vibe coding berbasis data.

Seluruh angka dalam narasi dihitung dari dataset saat runtime, bukan
ditulis tetap. Bila dataset diganti atau diperluas, narasinya menyesuaikan.

Pembagian era memakai pendekatan adaptif: kuartal bervolume di bawah ambang
dikelompokkan sebagai prasejarah, sisanya dibagi tiga fase berdasarkan
urutan waktu. Pendekatan ini dipilih agar tidak bergantung pada tanggal
tetap yang bisa salah bila rentang data berubah.
"""

from __future__ import annotations

import pandas as pd

from . import data as D
from .theme import CERULEAN, DARK_SLATE, GOLDENROD, NEGATIVE, TUSCAN


def _fmt(n: float) -> str:
    """Format angka dengan pemisah ribuan gaya Indonesia."""
    return f"{int(round(n)):,}".replace(",", ".")


def _pct(x: float) -> str:
    return f"{x:.1f}%".replace(".", ",")


def headline_stats(df: pd.DataFrame, sent: pd.DataFrame) -> dict:
    """Statistik ringkas untuk kartu KPI dan pembuka narasi."""
    qv = D.quarter_volume(df)
    valid = qv[qv["posts"] >= D.MIN_QUARTER_DOCS]

    peak = qv.loc[qv["posts"].idxmax()] if len(qv) else None
    tools = D.tool_counts(df)

    stats = {
        "total": len(df),
        "start": df["created_dt"].min(),
        "end": df["created_dt"].max(),
        "quarters_total": df["quarter"].nunique(),
        "quarters_valid": len(valid),
        "peak_quarter": peak["quarter"] if peak is not None else "—",
        "peak_posts": int(peak["posts"]) if peak is not None else 0,
        "tool_mentions": int(df["tool_any"].sum()) if "tool_any" in df else 0,
        "top_tool": tools.iloc[0]["tool"] if len(tools) else "—",
        "top_tool_n": int(tools.iloc[0]["mentions"]) if len(tools) else 0,
        "median_engagement": float(df["engagement"].median()),
        "sent_coverage": len(sent),
    }

    # Konsentrasi volume: porsi post pada 4 kuartal terakhir
    if len(valid) >= 4:
        last4 = valid.tail(4)["posts"].sum()
        stats["last4_share"] = last4 / len(df) * 100
    else:
        stats["last4_share"] = float("nan")

    # Pertumbuhan dari kuartal valid pertama ke kuartal puncak
    if len(valid) >= 2:
        first = valid.iloc[0]
        stats["first_valid_quarter"] = first["quarter"]
        stats["first_valid_posts"] = int(first["posts"])
        stats["growth_multiple"] = (
            stats["peak_posts"] / first["posts"] if first["posts"] else float("nan")
        )
    else:
        stats["first_valid_quarter"] = "—"
        stats["first_valid_posts"] = 0
        stats["growth_multiple"] = float("nan")

    if len(sent):
        vc = sent["sentiment"].value_counts(normalize=True).mul(100)
        stats["pos"] = vc.get("positive", 0.0)
        stats["neu"] = vc.get("neutral", 0.0)
        stats["neg"] = vc.get("negative", 0.0)
        stats["net"] = stats["pos"] - stats["neg"]

        sq = D.sentiment_by_quarter(sent)
        if len(sq) >= 2:
            stats["net_first"] = float(sq.iloc[0]["net"])
            stats["net_last"] = float(sq.iloc[-1]["net"])
            stats["net_shift"] = stats["net_last"] - stats["net_first"]
            stats["net_first_q"] = sq.iloc[0]["quarter"]
            stats["net_last_q"] = sq.iloc[-1]["quarter"]
        else:
            stats["net_shift"] = float("nan")
    else:
        stats["net_shift"] = float("nan")

    return stats


def build_eras(df: pd.DataFrame, sent: pd.DataFrame) -> list[dict]:
    """Bangun daftar era beserta narasi dan angka pendukungnya."""
    qv = D.quarter_volume(df)
    valid = qv[qv["posts"] >= D.MIN_QUARTER_DOCS].reset_index(drop=True)
    sparse = qv[qv["posts"] < D.MIN_QUARTER_DOCS]

    eras: list[dict] = []

    # --- Era 0: prasejarah ---
    if len(sparse):
        eras.append(
            {
                "tag": "Prasejarah",
                "color": GOLDENROD,
                "title": f"{sparse.iloc[0]['quarter']} – {sparse.iloc[-1]['quarter']}"
                f" · {_fmt(sparse['posts'].sum())} post",
                "body": (
                    f"Sepanjang <b class='hl'>{len(sparse)} kuartal</b> pertama, istilah ini "
                    f"praktis tidak beredar: total hanya <b class='hl'>{_fmt(sparse['posts'].sum())} post</b>. "
                    f"Beberapa kuartal berisi <strong>satu post tunggal</strong>. "
                    "Kuartal-kuartal ini dikecualikan dari seluruh analisis tren, karena "
                    "satu post otomatis berarti pangsa 100% dan akan menghasilkan "
                    "\"tren\" yang sepenuhnya artefak bila diperlakukan setara dengan "
                    "kuartal berisi ribuan post."
                ),
            }
        )

    if not len(valid):
        return eras

    # --- Bagi kuartal valid menjadi tiga fase ---
    n = len(valid)
    cut1 = max(1, n // 3)
    cut2 = max(cut1 + 1, (2 * n) // 3)
    phases = [
        ("Ledakan", CERULEAN, valid.iloc[:cut1]),
        ("Arus utama", DARK_SLATE, valid.iloc[cut1:cut2]),
        ("Pendewasaan", TUSCAN, valid.iloc[cut2:]),
    ]

    sq = D.sentiment_by_quarter(sent) if len(sent) else pd.DataFrame()
    tsq = D.tool_share_by_quarter(df)

    for tag, color, block in phases:
        if not len(block):
            continue

        q_from, q_to = block.iloc[0]["quarter"], block.iloc[-1]["quarter"]
        posts = int(block["posts"].sum())
        share_of_all = posts / len(df) * 100

        # Tool dominan pada fase ini
        tool_txt = ""
        if len(tsq):
            blk = tsq[tsq["quarter"].isin(block["quarter"])]
            if len(blk):
                agg = (
                    blk.groupby("tool")["mentions"].sum().sort_values(ascending=False)
                )
                if len(agg) and agg.iloc[0] > 0:
                    top3 = ", ".join(
                        f"<strong>{t}</strong> ({_fmt(v)})"
                        for t, v in agg.head(3).items()
                        if v > 0
                    )
                    tool_txt = f" Tool paling banyak disebut: {top3}."

        # Sentimen pada fase ini
        sent_txt = ""
        if len(sq):
            blk = sq[sq["quarter"].isin(block["quarter"])]
            if len(blk):
                net = blk["net"].mean()
                pos = blk["positive"].mean()
                neg = blk["negative"].mean()
                arah = "positif" if net > 0 else "negatif"
                sent_txt = (
                    f" Sentimen rata-rata <b class='hl'>{_pct(pos)} positif</b> "
                    f"berbanding {_pct(neg)} negatif, "
                    f"net {arah} {_pct(abs(net))}."
                )

        # Pertumbuhan dalam fase
        growth_txt = ""
        if len(block) >= 2:
            a, b = int(block.iloc[0]["posts"]), int(block.iloc[-1]["posts"])
            if a > 0:
                delta = (b - a) / a * 100
                arah = "naik" if delta >= 0 else "turun"
                growth_txt = (
                    f" Volume {arah} dari {_fmt(a)} ke {_fmt(b)} post per kuartal "
                    f"({_pct(abs(delta))})."
                )

        eras.append(
            {
                "tag": tag,
                "color": color,
                "title": f"{q_from} – {q_to} · {_fmt(posts)} post "
                f"({_pct(share_of_all)} dari total)",
                "body": (
                    f"Fase ini menyumbang <b class='hl'>{_fmt(posts)} post</b>, "
                    f"{_pct(share_of_all)} dari seluruh dataset.{growth_txt}"
                    f"{tool_txt}{sent_txt}"
                ),
            }
        )

    return eras


def key_findings(df: pd.DataFrame, sent: pd.DataFrame, stats: dict) -> list[str]:
    """Daftar temuan utama, seluruhnya dihitung dari data."""
    out: list[str] = []

    span_days = (stats["end"] - stats["start"]).days
    out.append(
        f"Dataset memuat **{_fmt(stats['total'])} post** sepanjang "
        f"**{span_days} hari** ({stats['start']:%b %Y} – {stats['end']:%b %Y}), "
        f"tersebar di {stats['quarters_total']} kuartal — namun hanya "
        f"**{stats['quarters_valid']} kuartal** bervolume memadai untuk analisis tren."
    )

    if stats["quarters_valid"] >= 2 and stats["growth_multiple"] == stats["growth_multiple"]:
        out.append(
            f"Volume melonjak **{stats['growth_multiple']:.0f}×** dari "
            f"{_fmt(stats['first_valid_posts'])} post di {stats['first_valid_quarter']} "
            f"menjadi {_fmt(stats['peak_posts'])} post di puncaknya "
            f"(**{stats['peak_quarter']}**)."
        )

    if stats["last4_share"] == stats["last4_share"]:
        out.append(
            f"Percakapan sangat terkonsentrasi di masa terakhir: "
            f"**{_pct(stats['last4_share'])}** dari seluruh post terjadi dalam "
            f"4 kuartal terakhir. Ini istilah yang muda, bukan yang tumbuh perlahan."
        )

    tools = D.tool_counts(df)
    if len(tools) >= 3:
        top = tools.head(3)
        lst = ", ".join(f"**{r.tool}** ({_fmt(r.mentions)})" for r in top.itertuples())
        out.append(
            f"Tool paling sering muncul: {lst}. Total "
            f"**{_fmt(stats['tool_mentions'])}** post "
            f"({_pct(stats['tool_mentions'] / stats['total'] * 100)}) menyebut "
            "setidaknya satu tool secara eksplisit."
        )

    if len(sent):
        out.append(
            f"Distribusi sentimen atas **{_fmt(len(sent))} post berlabel**: "
            f"**{_pct(stats['neu'])} netral**, {_pct(stats['pos'])} positif, "
            f"{_pct(stats['neg'])} negatif. Dominasi netral wajar — banyak post "
            "berupa berbagi tautan, pengumuman, atau pertanyaan teknis, bukan penilaian."
        )

        if stats["net_shift"] == stats["net_shift"]:
            arah = "membaik" if stats["net_shift"] > 0 else "memburuk"
            out.append(
                f"Net sentiment **{arah} {abs(stats['net_shift']):.1f} poin** dari "
                f"{stats['net_first_q']} ({stats['net_first']:+.1f}) ke "
                f"{stats['net_last_q']} ({stats['net_last']:+.1f})."
            )

        st_tool = D.sentiment_by_tool(sent)
        if len(st_tool) >= 3:
            best, worst = st_tool.iloc[0], st_tool.iloc[-1]
            corr_note = ""
            if len(st_tool) >= 5:
                corr = st_tool["n"].corr(st_tool["net"])
                if corr == corr and corr < -0.3:
                    corr_note = (
                        " Terdapat korelasi negatif antara volume pembicaraan dan "
                        f"net sentiment (r = {corr:.2f}): tool yang paling banyak "
                        "dibahas justru paling banyak dikeluhkan — konsisten dengan "
                        "pemakaian intensif yang memunculkan lebih banyak friksi nyata."
                    )
            out.append(
                f"Net sentiment tertinggi **{best['tool']}** ({best['net']:+.1f}, "
                f"n={_fmt(best['n'])}); terendah **{worst['tool']}** "
                f"({worst['net']:+.1f}, n={_fmt(worst['n'])}).{corr_note}"
            )

    spikes = D.detect_spikes(df)
    if len(spikes):
        top = spikes.iloc[0]
        out.append(
            f"Terdeteksi **{len(spikes)} lonjakan harian** signifikan "
            f"(z ≥ 2,5 terhadap baseline bergerak 28 hari). Terbesar pada "
            f"**{top['date']:%d %b %Y}** dengan {int(top['posts'])} post "
            f"(z = {top['z']:.1f}, baseline {top['baseline']:.0f})."
        )

    return out


CONTEXT_NOTE = """
**Konteks eksternal.** Istilah *vibe coding* dipopulerkan Andrej Karpathy pada
Februari 2025 dan menyebar cepat sesudahnya. Konteks ini berasal dari
pengetahuan umum, **bukan** dari dataset ini — dataset hanya dapat menunjukkan
*kapan dan bagaimana* percakapan bergerak, bukan siapa yang memulainya.
Sebaran data yang menipis sebelum 2025 konsisten dengan penanggalan tersebut.
"""
