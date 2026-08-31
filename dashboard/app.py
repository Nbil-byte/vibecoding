"""Dashboard vibe coding — entry point Streamlit.

Jalankan dari root repo:
    streamlit run dashboard/app.py

Streamlit mengeksekusi file ini sebagai skrip (__main__), sehingga impor
relatif tidak bisa dipakai di sini. Root repo disisipkan ke sys.path agar
paket `dashboard` bisa diimpor secara absolut.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from dashboard import data as D  # noqa: E402
from dashboard.sections import (  # noqa: E402
    explorer,
    overview,
    sentiment,
    timeline,
    topics,
)
from dashboard.theme import (  # noqa: E402
    CSS,
    NEON_ICE,
    TEXT_MUTED,
    register_template,
)

st.set_page_config(
    page_title="Vibe Coding Dashboard",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

register_template()
st.markdown(CSS, unsafe_allow_html=True)

PAGES = {
    "Narasi": overview,
    "Timeline": timeline,
    "Sentimen": sentiment,
    "Topik & Tool": topics,
    "Jelajah Data": explorer,
}


@st.cache_data(show_spinner=False)
def _merge_sentiment(df: pd.DataFrame, sent: pd.DataFrame) -> pd.DataFrame:
    """Tempelkan kolom sentimen ke dataset utama lewat pencocokan teks.

    Pencocokan memakai teks, bukan indeks baris, karena file berlabel
    dihasilkan dari potongan baris dataset dan indeksnya tidak lagi selaras
    setelah baris tanpa tanggal valid dibuang.
    """
    if not len(sent):
        return df

    cols = [c for c in ("text", "sentiment", "sentiment_score") if c in sent.columns]
    lookup = sent[cols].drop_duplicates(subset="text")
    return df.merge(lookup, on="text", how="left")


def main() -> None:
    with st.sidebar:
        st.markdown(
            f"""<div style="margin-bottom:1.2rem">
              <div style="font-size:1.05rem;font-weight:700;color:{NEON_ICE}">
                ◆ VIBE CODING
              </div>
              <div style="font-size:.78rem;color:{TEXT_MUTED};letter-spacing:.04em">
                analisis diskursus X/Twitter
              </div>
            </div>""",
            unsafe_allow_html=True,
        )

        choice = st.radio("Halaman", list(PAGES), label_visibility="collapsed")
        st.divider()

    # --- Muat data ---
    try:
        with st.spinner("Memuat dataset ..."):
            df = D.tag_tools(D.load_main())
            sent_raw = D.load_sentiment()
            topic_artifacts = D.load_topics()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.markdown(
            """<div class="vc-warn">
            Dataset tidak ditemukan. Jalankan scraper lebih dulu, atau letakkan
            CSV hasil scraping di <code>data/raw/</code>.<br><br>
            <code>python playwright_scraper.py --login</code><br>
            <code>python playwright_scraper.py --cookies cookies.json --headless --target-rows 10000</code>
            </div>""",
            unsafe_allow_html=True,
        )
        st.stop()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Gagal memuat data: {type(exc).__name__}: {exc}")
        st.stop()

    sent = D.tag_tools(sent_raw) if len(sent_raw) else sent_raw
    df_full = _merge_sentiment(df, sent_raw)

    # --- Info sumber data di sidebar ---
    with st.sidebar:
        st.caption("Sumber data")
        st.markdown(
            f"""<div style="font-size:.78rem;color:{TEXT_MUTED};line-height:1.75">
              <div><b>{df.attrs.get('source', '—')}</b></div>
              <div>{len(df):,} post valid</div>
              <div>{df['created_dt'].min():%b %Y} – {df['created_dt'].max():%b %Y}</div>
              <div style="margin-top:.5rem">
                Berlabel sentimen: <b>{len(sent_raw):,}</b>
                ({len(sent_raw) / len(df) * 100:.0f}%)
              </div>
              <div>Artefak topik: <b>{len(topic_artifacts)}/4</b></div>
            </div>""".replace(",", "."),
            unsafe_allow_html=True,
        )
        dropped = df.attrs.get("dropped_invalid", 0)
        if dropped:
            st.caption(f"{dropped} baris dibuang (tanggal/teks tidak valid)")

        st.divider()
        st.caption(
            "Dibangun dari `sentiment_colab.ipynb`, `topic_modeling.ipynb`, "
            "dan `timeline_analysis.ipynb`."
        )

    # --- Render halaman terpilih ---
    PAGES[choice].render(df_full, sent, topic_artifacts)


if __name__ == "__main__":
    main()
