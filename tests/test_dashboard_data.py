"""Test lapisan data dashboard.

Dijalankan dengan:
    python -m pytest tests/ -v

Test yang menyentuh dataset nyata akan di-skip otomatis bila file tidak ada,
sehingga suite tetap hijau di lingkungan tanpa data (mis. CI).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard import data as D  # noqa: E402


# --- Helper: dataset sintetis ---
def make_df(rows: int = 200, start: str = "2025-01-01") -> pd.DataFrame:
    dates = pd.date_range(start, periods=rows, freq="D")
    return pd.DataFrame(
        {
            "created_at": dates.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "text": [f"vibe coding with cursor post {i}" for i in range(rows)],
            "username": [f"user{i % 7}" for i in range(rows)],
            "like_count": range(rows),
            "repost_count": [1] * rows,
            "reply_count": [2] * rows,
            "view_count": [100] * rows,
        }
    )


# --- Deteksi delimiter ---
@pytest.mark.parametrize(
    "header,expected",
    [
        ("a;b;c\n", ";"),
        ("a,b,c\n", ","),
        ("a\tb\tc\n", "\t"),
    ],
)
def test_sniff_sep(tmp_path, header, expected):
    """Delimiter harus terdeteksi, bukan diasumsikan koma.

    Ini penting karena vibecoding_relevant_10000.csv memakai ';' sementara
    file keluaran sentimen memakai ','.
    """
    p = tmp_path / "x.csv"
    p.write_text(header + "1" + expected + "2" + expected + "3\n", encoding="utf-8")
    assert D._sniff_sep(p) == expected


def test_read_csv_smart_semicolon(tmp_path):
    p = tmp_path / "semi.csv"
    p.write_text("created_at;text\n2025-01-01T00:00:00.000Z;halo\n", encoding="utf-8")
    df = D.read_csv_smart(p)
    assert list(df.columns) == ["created_at", "text"]
    assert len(df) == 1


# --- Normalisasi ---
def test_normalise_drops_invalid_dates():
    df = make_df(10)
    df.loc[0, "created_at"] = "bukan-tanggal"
    df.loc[1, "created_at"] = None
    out = D._normalise(df)
    assert len(out) == 8
    assert out.attrs["dropped_invalid"] == 2


def test_normalise_requires_columns():
    with pytest.raises(ValueError, match="Kolom wajib"):
        D._normalise(pd.DataFrame({"foo": [1]}))


def test_normalise_renames_repost_to_retweet():
    out = D._normalise(make_df(5))
    assert "retweet_count" in out.columns
    assert "engagement" in out.columns


def test_normalise_deduplicates_text():
    df = make_df(5)
    df["text"] = "teks identik"
    out = D._normalise(df)
    assert len(out) == 1, "post identik harus dibuang agar tidak membentuk spike palsu"


def test_normalise_adds_period_columns():
    out = D._normalise(make_df(5, start="2025-02-10"))
    assert out["quarter"].iloc[0] == "2025Q1"
    assert out["month"].iloc[0] == "2025-02"


# --- Deteksi tool ---
def test_tag_tools_detects_and_is_not_exclusive():
    df = D._normalise(make_df(3))
    df.loc[0, "text"] = "pakai claude dan cursor bareng"
    tagged = D.tag_tools(df)
    assert tagged.loc[0, "tool_Claude"]
    assert tagged.loc[0, "tool_Cursor"]
    assert tagged.loc[0, "tool_any"]


def test_tag_tools_word_boundary():
    """Regex harus memakai batas kata agar tidak salah tangkap substring."""
    df = D._normalise(make_df(2))
    df.loc[0, "text"] = "recursor bukan cursor sebenarnya"
    df.loc[1, "text"] = "tidak ada tool apa pun di sini"
    tagged = D.tag_tools(df)
    assert tagged.loc[0, "tool_Cursor"], "'cursor' berdiri sendiri harus tertangkap"
    assert not tagged.loc[1, "tool_any"]


# --- Ambang kuartal ---
def test_valid_quarters_filters_micro_volume():
    """Kuartal bervolume mikro harus dibuang.

    Ini pengaman inti: kuartal berisi 1 post bernilai pangsa 100% dan bila
    diperlakukan setara kuartal besar akan menghasilkan tren palsu.
    """
    big = make_df(120, start="2025-04-01")      # 2025Q2-Q3, volume besar
    tiny = make_df(2, start="2022-04-01")       # 2022Q2, hanya 2 post
    tiny["text"] = ["post langka a", "post langka b"]

    df = D._normalise(pd.concat([big, tiny], ignore_index=True))
    quarters = D.valid_quarters(df, min_docs=30)

    assert "2022Q2" not in quarters
    assert all(df[df["quarter"] == q].shape[0] >= 30 for q in quarters)


def test_quarter_volume_cumulative_and_growth():
    df = D._normalise(make_df(200, start="2025-01-01"))
    qv = D.quarter_volume(df)
    assert qv["cumulative"].iloc[-1] == len(df)
    assert qv["cumulative"].is_monotonic_increasing


# --- Deteksi spike ---
def test_detect_spikes_uses_moving_baseline():
    """Lonjakan diukur relatif terhadap baseline bergerak, bukan rata-rata global.

    Volume dasar naik sepanjang periode; terhadap rata-rata global, seluruh
    periode akhir akan tampak sebagai lonjakan padahal hanya pertumbuhan.
    """
    # Volume naik bertahap, tanpa anomali mendadak
    parts = []
    for i, n in enumerate([5, 10, 20, 40, 80]):
        block = make_df(n, start=f"2025-0{i + 1}-01")
        block["text"] = [f"pertumbuhan wajar {i}-{j}" for j in range(n)]
        parts.append(block)
    df = D._normalise(pd.concat(parts, ignore_index=True))

    spikes = D.detect_spikes(df, z_threshold=2.5)
    # Pertumbuhan bertahap tidak boleh dianggap lonjakan
    assert len(spikes) == 0


def test_detect_spikes_finds_real_anomaly():
    base = make_df(90, start="2025-01-01")
    base["text"] = [f"harian normal {i}" for i in range(90)]

    burst_day = "2025-03-15"
    burst = pd.DataFrame(
        {
            "created_at": [f"{burst_day}T10:00:00.000Z"] * 60,
            "text": [f"ledakan {i}" for i in range(60)],
            "username": ["u"] * 60,
            "like_count": [1] * 60,
            "repost_count": [0] * 60,
            "reply_count": [0] * 60,
            "view_count": [1] * 60,
        }
    )
    df = D._normalise(pd.concat([base, burst], ignore_index=True))
    spikes = D.detect_spikes(df, z_threshold=2.5)

    assert len(spikes) >= 1
    assert pd.Timestamp(burst_day) in set(spikes["date"])


# --- Sentimen ---
def test_sentiment_by_quarter_excludes_micro_quarters():
    df = make_df(120, start="2025-04-01")
    df["sentiment"] = (["positive"] * 60) + (["negative"] * 60)
    tiny = make_df(1, start="2022-04-01")
    tiny["text"] = ["satu satunya post"]
    tiny["sentiment"] = ["positive"]

    merged = D._normalise(pd.concat([df, tiny], ignore_index=True))
    sq = D.sentiment_by_quarter(merged, min_docs=30)

    assert "2022Q2" not in set(sq["quarter"]), (
        "kuartal 1 post akan bernilai net +100 dan mendistorsi tren"
    )
    assert {"negative", "neutral", "positive", "net"} <= set(sq.columns)


def test_sentiment_by_tool_respects_min_mentions():
    df = D._normalise(make_df(50))
    df["sentiment"] = "positive"
    tagged = D.tag_tools(df)
    out = D.sentiment_by_tool(tagged, min_mentions=10)
    # Semua teks sintetis menyebut cursor
    assert "Cursor" in set(out["tool"])
    high = D.sentiment_by_tool(tagged, min_mentions=999)
    assert len(high) == 0


# --- Istilah ---
def test_top_terms_removes_query_keywords():
    df = D._normalise(make_df(30))
    terms = D.top_terms(df, n=10)
    assert "vibe" not in set(terms["term"])
    assert "coding" not in set(terms["term"]), (
        "kata kunci query mendominasi setiap dokumen sehingga tidak informatif"
    )


# --- Integrasi dengan dataset nyata ---
@pytest.mark.parametrize("name", D.MAIN_CANDIDATES)
def test_real_dataset_loads(name):
    path = D.RAW_DIR / name
    if not path.exists():
        pytest.skip(f"{name} tidak tersedia")

    df = D._normalise(D.read_csv_smart(path))
    assert len(df) > 0
    assert df["created_dt"].notna().all()
    assert df["quarter"].str.match(r"^\d{4}Q[1-4]$").all()

    tagged = D.tag_tools(df)
    assert tagged["tool_any"].sum() > 0
