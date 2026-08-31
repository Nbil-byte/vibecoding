"""Pemuatan dan agregasi data untuk dashboard.

Semua fungsi memakai cache Streamlit agar dataset 10rb baris tidak dibaca
ulang setiap interaksi widget.

Catatan penting soal sumber data:

- `vibecoding_relevant_10000.csv` memakai delimiter ';' sementara file
  keluaran sentimen memakai ',' karena ditulis `DataFrame.to_csv`. Delimiter
  karena itu dideteksi otomatis, bukan diasumsikan.
- Kolom `created_at` mengandung nilai non-tanggal, sehingga parsing wajib
  memakai `errors="coerce"` lalu membuang baris tanpa tanggal valid.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

MAIN_CANDIDATES = [
    "vibecoding_relevant_10000.csv",
    "vibecoding_10000_broad_strict.csv",
    "vibecoding_10000_broad.csv",
    "vibecoding_strict.csv",
]

# Kuartal dengan dokumen di bawah ambang ini dibuang dari semua analisis tren.
# Kuartal berisi 1-2 post menghasilkan pangsa 100% yang menyesatkan bila
# dirata-ratakan setara dengan kuartal berisi ribuan post.
MIN_QUARTER_DOCS = 30

TOOL_PATTERNS = {
    "Claude": r"\bclaude\b|\banthropic\b|claude ?code",
    "Cursor": r"\bcursor\b",
    "Copilot": r"\bcopilot\b|github copilot",
    "Replit": r"\breplit\b",
    "Lovable": r"\blovable\b",
    "Bolt": r"\bbolt\.new\b|\bbolt\b",
    "ChatGPT/OpenAI": r"\bchatgpt\b|\bopenai\b|\bgpt-?[45]\b|\bcodex\b",
    "Gemini/Google": r"\bgemini\b|\bgoogle ai\b|\bantigravity\b",
    "Windsurf": r"\bwindsurf\b|\bcodeium\b",
    "v0": r"\bv0\.dev\b|\bv0\b",
    "Devin": r"\bdevin\b",
}


def _sniff_sep(path: Path) -> str:
    """Deteksi delimiter dari baris header."""
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        head = fh.readline()
    try:
        return csv.Sniffer().sniff(head, delimiters=",;\t|").delimiter
    except csv.Error:
        # Fallback: pilih kandidat dengan kemunculan terbanyak di header
        return max(",;\t|", key=head.count)


def read_csv_smart(path: Path) -> pd.DataFrame:
    """Baca CSV dengan delimiter terdeteksi otomatis."""
    return pd.read_csv(
        path,
        sep=_sniff_sep(path),
        encoding="utf-8-sig",
        engine="python",
        on_bad_lines="skip",
    )


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """Samakan nama kolom, parse tanggal, buang baris tanpa tanggal/teks."""
    df = df.rename(columns={"repost_count": "retweet_count"})

    if "created_at" not in df.columns or "text" not in df.columns:
        raise ValueError(
            f"Kolom wajib tidak ditemukan. Kolom tersedia: {list(df.columns)}"
        )

    df["created_dt"] = pd.to_datetime(
        df["created_at"], errors="coerce", utc=True, format="mixed"
    )

    before = len(df)
    df = df[df["created_dt"].notna()].copy()
    df = df[df["text"].notna() & (df["text"].astype(str).str.strip() != "")]
    df.attrs["dropped_invalid"] = before - len(df)

    df["created_dt"] = df["created_dt"].dt.tz_convert(None)
    df["date"] = df["created_dt"].dt.date
    df["month"] = df["created_dt"].dt.to_period("M").astype(str)
    df["quarter"] = df["created_dt"].dt.to_period("Q").astype(str)

    for col in ("like_count", "retweet_count", "reply_count", "view_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["engagement"] = sum(
        df[c] for c in ("like_count", "retweet_count", "reply_count") if c in df.columns
    )

    # Buang duplikat teks agar spike tidak terbentuk dari post identik
    df = df.drop_duplicates(subset="text", keep="first")

    return df.sort_values("created_dt").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_main() -> pd.DataFrame:
    """Muat dataset utama hasil scraping."""
    for name in MAIN_CANDIDATES:
        path = RAW_DIR / name
        if path.exists():
            df = _normalise(read_csv_smart(path))
            df.attrs["source"] = name
            return df
    raise FileNotFoundError(
        "Dataset tidak ditemukan. Letakkan salah satu file berikut di data/raw/: "
        + ", ".join(MAIN_CANDIDATES)
    )


@st.cache_data(show_spinner=False)
def load_sentiment() -> pd.DataFrame:
    """Gabungkan seluruh file berlabel sentimen yang tersedia.

    Mengembalikan DataFrame kosong bila belum ada file berlabel.
    """
    frames = []
    for path in sorted(RAW_DIR.glob("*sentimen*.csv")) + sorted(
        PROCESSED_DIR.glob("*sentimen*.csv")
    ):
        try:
            part = read_csv_smart(path)
        except Exception:
            continue
        if "sentiment" in part.columns:
            frames.append(part)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = _normalise(df)
    df = df.drop_duplicates(subset="text", keep="first")
    df["sentiment"] = df["sentiment"].str.lower().str.strip()
    return df[df["sentiment"].isin(["negative", "neutral", "positive"])]


@st.cache_data(show_spinner=False)
def load_topics() -> dict[str, pd.DataFrame]:
    """Muat artefak BERTopic bila ada.

    Notebook menyimpan CSV ini di direktori kerjanya (root repo bila lokal,
    atau lingkungan Colab bila remote). Dashboard mencari di root dan di
    data/processed/.
    """
    wanted = {
        "docs": "vibecoding_topics_docs.csv",
        "summary": "vibecoding_topics_summary.csv",
        "quarter": "vibecoding_topics_per_quarter.csv",
        "diagnostics": "vibecoding_topics_diagnostics.csv",
    }
    out: dict[str, pd.DataFrame] = {}
    for key, fname in wanted.items():
        for base in (ROOT, PROCESSED_DIR, RAW_DIR):
            path = base / fname
            if path.exists():
                try:
                    out[key] = read_csv_smart(path)
                except Exception:
                    pass
                break
    return out


def tag_tools(df: pd.DataFrame) -> pd.DataFrame:
    """Tambahkan kolom boolean per tool berdasarkan pencocokan regex teks.

    Satu post bisa menyebut beberapa tool sekaligus, jadi kolomnya independen
    dan tidak saling eksklusif.
    """
    text = df["text"].astype(str).str.lower()
    out = df.copy()
    for tool, pattern in TOOL_PATTERNS.items():
        out[f"tool_{tool}"] = text.str.contains(pattern, regex=True, na=False)
    out["tool_any"] = out[[f"tool_{t}" for t in TOOL_PATTERNS]].any(axis=1)
    return out


def tool_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Jumlah penyebutan per tool, terurut menurun."""
    rows = [
        {"tool": tool, "mentions": int(df[f"tool_{tool}"].sum())}
        for tool in TOOL_PATTERNS
        if f"tool_{tool}" in df.columns
    ]
    if not rows:
        return pd.DataFrame(columns=["tool", "mentions"])
    return (
        pd.DataFrame(rows)
        .sort_values("mentions", ascending=False)
        .reset_index(drop=True)
    )


def valid_quarters(df: pd.DataFrame, min_docs: int = MIN_QUARTER_DOCS) -> list[str]:
    """Kuartal dengan jumlah post memadai untuk analisis tren."""
    counts = df["quarter"].value_counts()
    return sorted(counts[counts >= min_docs].index.tolist())


def quarter_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Volume post per kuartal beserta pertumbuhan dan kumulatifnya."""
    g = (
        df.groupby("quarter")
        .agg(posts=("text", "size"), engagement=("engagement", "sum"))
        .reset_index()
        .sort_values("quarter")
    )
    g["cumulative"] = g["posts"].cumsum()
    g["growth_%"] = g["posts"].pct_change().mul(100).round(1)
    return g


def month_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Volume post per bulan."""
    return (
        df.groupby("month")
        .agg(posts=("text", "size"), engagement=("engagement", "sum"))
        .reset_index()
        .sort_values("month")
    )


def daily_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Volume harian dengan rata-rata bergerak 7 hari."""
    g = df.groupby("date").size().reset_index(name="posts")
    g["date"] = pd.to_datetime(g["date"])
    g = g.set_index("date").asfreq("D", fill_value=0).reset_index()
    g["ma7"] = g["posts"].rolling(7, min_periods=1).mean()
    return g


def detect_spikes(df: pd.DataFrame, z_threshold: float = 2.5) -> pd.DataFrame:
    """Deteksi lonjakan harian memakai z-score terhadap rata-rata bergerak 28 hari.

    Baseline bergerak dipakai (bukan rata-rata global) karena volume dasar
    naik drastis sepanjang periode. Terhadap rata-rata global, hampir setiap
    hari di 2026 akan tampak sebagai "spike" padahal itu hanya pertumbuhan.
    """
    g = daily_volume(df)
    g["baseline"] = g["posts"].rolling(28, min_periods=7).mean()
    g["sd"] = g["posts"].rolling(28, min_periods=7).std()
    g["z"] = (g["posts"] - g["baseline"]) / g["sd"].replace(0, np.nan)

    spikes = g[(g["z"] >= z_threshold) & (g["posts"] >= 5)].copy()
    return spikes.sort_values("z", ascending=False).reset_index(drop=True)


def spike_examples(df: pd.DataFrame, day, n: int = 3) -> pd.DataFrame:
    """Post dengan engagement tertinggi pada tanggal tertentu."""
    day = pd.to_datetime(day).date()
    sub = df[df["date"] == day]
    cols = [c for c in ("username", "text", "engagement", "post_url") if c in sub.columns]
    return sub.nlargest(n, "engagement")[cols]


def sentiment_by_quarter(df: pd.DataFrame, min_docs: int = MIN_QUARTER_DOCS) -> pd.DataFrame:
    """Pangsa sentimen per kuartal, hanya kuartal bervolume memadai."""
    keep = valid_quarters(df, min_docs)
    sub = df[df["quarter"].isin(keep)]
    counts = (
        sub.groupby(["quarter", "sentiment"]).size().unstack(fill_value=0).sort_index()
    )
    for col in ("negative", "neutral", "positive"):
        if col not in counts.columns:
            counts[col] = 0
    share = counts.div(counts.sum(axis=1), axis=0).mul(100).round(1)
    share["posts"] = counts.sum(axis=1)
    share["net"] = (share["positive"] - share["negative"]).round(1)
    return share.reset_index()


def sentiment_by_tool(df: pd.DataFrame, min_mentions: int = 10) -> pd.DataFrame:
    """Pangsa sentimen dan net sentiment per tool."""
    rows = []
    for tool in TOOL_PATTERNS:
        col = f"tool_{tool}"
        if col not in df.columns:
            continue
        sub = df[df[col]]
        if len(sub) < min_mentions:
            continue
        vc = sub["sentiment"].value_counts(normalize=True).mul(100)
        rows.append(
            {
                "tool": tool,
                "n": len(sub),
                "positive": round(vc.get("positive", 0.0), 1),
                "neutral": round(vc.get("neutral", 0.0), 1),
                "negative": round(vc.get("negative", 0.0), 1),
                "net": round(vc.get("positive", 0.0) - vc.get("negative", 0.0), 1),
            }
        )
    cols = ["tool", "n", "positive", "neutral", "negative", "net"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows).sort_values("net", ascending=False).reset_index(drop=True)


def tool_share_by_quarter(df: pd.DataFrame, min_docs: int = MIN_QUARTER_DOCS) -> pd.DataFrame:
    """Pangsa penyebutan tiap tool per kuartal (persen dari post bertool)."""
    keep = valid_quarters(df, min_docs)
    sub = df[df["quarter"].isin(keep)]
    rows = []
    for quarter, grp in sub.groupby("quarter"):
        total = int(grp["tool_any"].sum())
        if total == 0:
            continue
        for tool in TOOL_PATTERNS:
            col = f"tool_{tool}"
            if col in grp.columns:
                rows.append(
                    {
                        "quarter": quarter,
                        "tool": tool,
                        "mentions": int(grp[col].sum()),
                        "share": round(grp[col].sum() / total * 100, 1),
                    }
                )
    if not rows:
        return pd.DataFrame(columns=["quarter", "tool", "mentions", "share"])
    return pd.DataFrame(rows)


def top_terms(df: pd.DataFrame, n: int = 25, min_len: int = 4) -> pd.DataFrame:
    """Kata paling sering muncul setelah stopword dibuang.

    Dipakai sebagai pengganti ringan ketika artefak BERTopic belum tersedia.
    Ini BUKAN topic modeling: tidak ada clustering semantik di sini.
    """
    stop = {
        "vibe", "vibes", "coding", "code", "coded", "coder", "vibecoding", "vibecode",
        "that", "this", "with", "from", "have", "just", "like", "what", "when", "your",
        "they", "them", "then", "than", "will", "would", "could", "should", "about",
        "there", "here", "been", "being", "more", "most", "very", "really", "some",
        "into", "over", "only", "also", "even", "still", "much", "make", "made",
        "yang", "dan", "untuk", "dengan", "pada", "adalah", "tidak", "bisa", "akan",
        "sudah", "saya", "kamu", "kita", "mereka", "juga", "saja", "buat", "lagi",
        "dalam", "atau", "karena", "sangat", "lebih", "https", "http", "amp",
    }
    words = (
        df["text"].astype(str).str.lower()
        .str.replace(r"http\S+", " ", regex=True)
        .str.replace(r"@\w+", " ", regex=True)
        .str.replace(r"[^a-z\s]", " ", regex=True)
        .str.split()
        .explode()
    )
    words = words[(words.str.len() >= min_len) & (~words.isin(stop))]
    if not len(words):
        return pd.DataFrame(columns=["term", "count"])
    return (
        words.value_counts()
        .head(n)
        .rename_axis("term")
        .reset_index(name="count")
    )
