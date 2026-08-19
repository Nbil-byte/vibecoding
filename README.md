# Analisis Diskursus *Vibe Coding* di X/Twitter

Pipeline riset lengkap untuk memetakan bagaimana istilah *vibe coding* dibicarakan di X/Twitter: dari scraping data, pelabelan sentimen multilingual, sampai topic modeling per kuartal.

Dataset acuan: ~10.000 post relevan, rentang **Mei 2022 – Juli 2026**, campuran bahasa (Inggris, Indonesia, Spanyol, Portugis, Jepang, Mandarin).

## Isi Repo

| File | Peran |
|---|---|
| `playwright_scraper.py` | Scraper utama berbasis Playwright (tahan Cloudflare) |
| `scraper.py` | Scraper alternatif berbasis `twscrape` |
| `label_sentimen.py` | Pelabelan sentimen batch via CLI |
| `sentiment_colab.ipynb` | Analisis sentimen: distribusi, tren kuartalan, sentimen per tool |
| `topic_modeling.ipynb` | BERTopic per kuartal + diagnostik kualitas topik |
| `timeline_analysis.ipynb` | Tren volume, kurva adopsi, deteksi spike harian |
| `analysis.ipynb` | Eksplorasi gabungan dan narrative timeline |

## Alur Kerja

```
scraping                  pelabelan                 analisis
─────────                 ─────────                 ────────
playwright_scraper.py  →  label_sentimen.py     →   sentiment_colab.ipynb
      atau                (atau langsung di          topic_modeling.ipynb
   scraper.py               notebook)                timeline_analysis.ipynb
      ↓                                                    ↓
data/raw/*.csv                                     CSV hasil + grafik
```

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

Untuk tahap analisis (sentimen dan topic modeling), dependensinya lebih berat dan terpisah:

```powershell
pip install -r requirements-analysis.txt
```

Notebook `sentiment_colab.ipynb` dan `topic_modeling.ipynb` juga bisa dijalankan langsung di Google Colab — keduanya punya sel instalasi sendiri dan widget upload CSV, jadi tidak perlu setup lokal.

---

# Bagian 1 — Scraping

## Login Manual dengan Playwright (direkomendasikan)

Jika `twscrape` gagal login karena Cloudflare, gunakan scraper Playwright:

```powershell
python playwright_scraper.py --login
```

Browser Edge/Chromium akan terbuka. Login X secara manual sampai halaman home terbuka, lalu kembali ke terminal dan tekan `ENTER`. Session akan disimpan di profile browser lokal:

```text
sessions/x_profile
```

Jika pilihan Gmail stuck, coba login X memakai username/email dan password langsung. Jika Edge bermasalah, coba Chrome:

```powershell
python playwright_scraper.py --login --browser-channel chrome
```

Setelah session tersimpan, jalankan scraping:

```powershell
python playwright_scraper.py --cookies cookies.json --browser-channel bundled --headless --scrolls-per-window 5
```

Untuk uji coba lebih cepat:

```powershell
python playwright_scraper.py --cookies cookies.json --browser-channel bundled --headless --chunk-days 365 --scrolls-per-window 2 --max-windows 2
```

Kalau mau lebih banyak data:

```powershell
python playwright_scraper.py --cookies cookies.json --browser-channel bundled --headless --chunk-days 180 --scrolls-per-window 10 --target-rows 10000
```

Untuk target besar seperti 10.000 row, gunakan window tanggal lebih kecil dan scroll lebih banyak:

```powershell
python playwright_scraper.py --cookies cookies.json --browser-channel bundled --headless --chunk-days 30 --scrolls-per-window 25 --delay-ms 1500 --target-rows 10000 --output data/raw/vibecoding_10000.csv
```

### Soal filter relevansi

Jangan longgarkan `--relevant-keywords` dengan keyword umum seperti `copilot`, `cursor`, `windsurf`, atau `ai coding` untuk dataset final karena hasilnya mudah keluar konteks. Scraper secara default memakai strict context filter agar data yang disimpan tetap mengandung konteks inti `vibe coding`.

Jika hasil tidak mencapai 10.000, berarti X tidak menampilkan cukup banyak post relevan untuk query tersebut lewat halaman search. Lebih baik turunkan target atau perluas periode/topik secara terkontrol, bukan memasukkan keyword tool umum.

Default query Playwright difokuskan ke konteks `vibe coding`/`vibecoding` dan hasil CSV juga difilter memakai keyword relevansi. Jika perlu, ubah filter:

```powershell
python playwright_scraper.py --cookies cookies.json --browser-channel bundled --headless --relevant-keywords "vibecoding,vibe coding,vibe-coding,vibe coded"
```

Output default:

```text
data/raw/x_playwright_vibecoding_5y_YYYYMMDD_HHMMSS.csv
```

## Login Akun X untuk `twscrape`

`twscrape` tidak bisa login memakai Google API. Jika akun X dibuat dengan "Sign in with Google", tetap perlu password akun X atau setup login X yang bisa dipakai langsung.

Format login yang dipakai `twscrape`:

```text
username:password:email:email_password
```

Untuk Gmail, `email_password` biasanya perlu memakai **App Password**, bukan password Google biasa.

Login saja:

```powershell
python scraper.py --login-only --username USERNAME_ANDA --email EMAIL_ANDA
```

Password X dan email password/app password akan diminta lewat prompt tersembunyi.

Login lalu langsung scraping:

```powershell
python scraper.py --login --username USERNAME_ANDA --email EMAIL_ANDA --limit-per-window 50
```

Jika akun X meminta 2FA, captcha, atau security challenge, login otomatis masih bisa gagal.

## Inject Cookies Browser ke `twscrape`

Jika login otomatis `twscrape` diblokir Cloudflare, login X lewat browser biasa lalu export cookies `x.com` memakai extension seperti **Cookie-Editor**.

Pastikan cookies yang diexport berisi minimal `auth_token` dan `ct0`.

Simpan file cookies di project, misalnya `cookies_x.json`, lalu inject ke akun `twscrape`:

```powershell
python scraper.py --inject-cookies-only --username USERNAME_ANDA --cookies cookies_x.json
```

Setelah status akun aktif, jalankan scraping:

```powershell
python scraper.py --query "(vibecoding OR \"vibe coding\" OR \"AI coding\" OR \"ngoding pakai AI\" OR \"kode pakai AI\")" --limit-per-window 100
```

> **File `cookies*.json` sudah masuk `.gitignore`. Jangan pernah commit file cookies** — isinya token sesi yang setara dengan akses penuh ke akun X kamu.

## Scraping Data 5 Tahun Belakang

```powershell
python scraper.py --query "(vibecoding OR \"vibe coding\" OR \"AI coding\" OR \"ngoding pakai AI\" OR \"kode pakai AI\")" --limit-per-window 100
```

Script otomatis membuat query bertanggal selama 5 tahun terakhir memakai filter `since:YYYY-MM-DD until:YYYY-MM-DD`. Default rentang per batch adalah 30 hari:

```powershell
python scraper.py --chunk-days 7 --limit-per-window 50
```

Output default `data/raw/tweets_vibecoding_5y_YYYYMMDD_HHMMSS.csv`, atau tentukan manual:

```powershell
python scraper.py --output data/raw/vibecoding.csv
```

## Kolom CSV Hasil Scraping

`tweet_id`, `created_at`, `text`, `author_id`, `username`, `displayname`, `lang`, `like_count`, `retweet_count`, `reply_count`, `quote_count`, `view_count`, `url`, `search_query`, `since`, `until`

---

# Bagian 2 — Analisis Sentimen

Model: [`cardiffnlp/twitter-xlm-roberta-base-sentiment`](https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment) — multilingual, dilatih pada teks Twitter. Label: `negative`, `neutral`, `positive`.

## Lewat CLI

```powershell
python label_sentimen.py              # baris 1000-2000 (default)
python label_sentimen.py 0 1000       # baris 0-1000
python label_sentimen.py 2000 1000    # baris 2000-3000
```

Input dibaca dari `data/raw/vibecoding_relevant_10000.csv`, output ke `data/raw/vibecoding_sentimen_{start}_{end}.csv`.

## Lewat Notebook

`sentiment_colab.ipynb` menjalankan seluruh dataset sekaligus dan menghasilkan:

- Distribusi sentimen (bar + pie) dan sebaran skor keyakinan
- Contoh tweet berkeyakinan tertinggi per label
- Tren sentimen per kuartal (volume + proporsi)
- Sentimen per tool (Claude, Cursor, Copilot, Replit, Lovable, Bolt, ChatGPT, Gemini, Windsurf) beserta *net sentiment*
- Sentimen vs engagement

Kolom keluaran: `sentiment`, `sentiment_score`, `prob_negative`, `prob_neutral`, `prob_positive`.

## Keterbatasan yang perlu diingat

Preprocessing dijaga **minimal** — hanya URL dan mention yang dibuang. Emoji dan tanda baca dipertahankan karena membawa sinyal sentimen.

- `MAX_LENGTH = 128` token memotong tweet sangat panjang. Naikkan ke 256 bila butuh konteks penuh, dengan biaya waktu inferensi.
- Prediksi dengan `sentiment_score < 0.5` sebaiknya ditinjau manual bila dipakai untuk klaim kuantitatif. Pada dataset acuan, porsi ini mencapai ~25%.
- Ironi dan sarkasme tetap sulit. Kalimat seperti *"vibe coding is amazing until production crashes"* sering terklasifikasi kurang tepat.

---

# Bagian 3 — Topic Modeling

`topic_modeling.ipynb` memakai [BERTopic](https://maartengr.github.io/BERTopic/) dengan embedding `paraphrase-multilingual-MiniLM-L12-v2`.

Susunan pipeline: UMAP (reduksi dimensi) → HDBSCAN (clustering) → c-TF-IDF (ekstraksi kata kunci).

## Yang dihasilkan

- Daftar topik + kata kunci + contoh dokumen
- Diagnostik kualitas topik (lihat bawah)
- Distribusi dan pangsa topik per kuartal
- Heatmap evolusi topik antar waktu
- Topik yang menguat dan meredup
- Topik dominan per tool AI coding

## Parameter yang paling berpengaruh

Semuanya terkumpul di sel impor:

| Parameter | Default | Efek |
|---|---|---|
| `MIN_TOPIC_SIZE` | `30` | Pengatur granularitas utama; kecil = banyak topik sempit |
| `MIN_SAMPLES` | `10` | Lebih kecil dari `MIN_TOPIC_SIZE` membuat clustering longgar dan menekan outlier |
| `CLUSTER_METHOD` | `"leaf"` | `"leaf"` memecah halus dan menghindari topik catch-all; `"eom"` menghasilkan sedikit klaster besar |
| `NR_TOPICS` | `None` | Sengaja dimatikan — reduksi paksa dapat menggabung topik tak berhubungan menjadi klaster sampah |
| `REDUCE_OUTLIERS` | `True` | Menugaskan ulang outlier ke topik terdekat |
| `MIN_QUARTER_DOCS` | `30` | Membuang kuartal bervolume mikro dari analisis tren |
| `COHERENCE_FLOOR` | `0.30` | Batas koherensi untuk menandai topik meragukan |

## Diagnostik kualitas topik

Tidak semua klaster bermakna. HDBSCAN bisa menghasilkan klaster "sisa" yang menyatukan dokumen tak berhubungan, dan c-TF-IDF akan tetap memberinya kata kunci yang tampak meyakinkan. Sel 6b menyaringnya dengan dua metrik:

- **Koherensi** — rata-rata cosine similarity dokumen ke centroid topiknya
- **Pangsa** — topik yang menampung porsi berlebihan patut dicurigai sebagai *catch-all*

Topik bertanda `SUSPECT` **jangan dipakai menarik kesimpulan** tanpa membaca sampel dokumennya lebih dulu.

## Dua jebakan metodologis yang ditangani

**1. Outlier HDBSCAN bukan sampel acak.** Yang tersingkir justru dokumen paling beragam. Tanpa reduksi, tingkat outlier bisa mencapai 50%, dan semua persentase yang dihitung dari subset berlabel tidak bisa digeneralisasi ke keseluruhan korpus.

`reduce_outliers()` tidak menghapus baris apa pun — hanya mengganti label, sehingga cakupan naik mendekati 100%. Trade-off-nya presisi: sebagian dokumen dipaksa masuk topik yang kurang cocok. Kolom `topic_raw` menyimpan penugasan asli agar dampaknya bisa diaudit:

```python
(df["topic_raw"] == -1).mean()                       # porsi yang semula outlier
df[df["topic_raw"] == -1]["topic"].value_counts()     # ke mana mereka pergi
```

**2. Kuartal bervolume mikro menciptakan tren palsu.** Pada dataset acuan, tiga kuartal hanya berisi **1 dokumen** (2022Q2, 2023Q3, 2024Q1). Satu dokumen otomatis berarti pangsa 100%. Bila pangsa antar kuartal dirata-ratakan tanpa bobot, kuartal semu itu mendominasi hasil dan memunculkan "penurunan" hingga −19 poin persen yang sepenuhnya artefak.

Dua pengaman dipasang: `MIN_QUARTER_DOCS` membuang kuartal mikro, dan pangsa paruh waktu dihitung dari **jumlah dokumen teragregasi**, bukan rata-rata pangsa antar kuartal.

## File keluaran

| File | Isi |
|---|---|
| `vibecoding_topics_docs.csv` | Dokumen + label topik (termasuk `topic_raw`) |
| `vibecoding_topics_summary.csv` | Ringkasan topik + kata kunci + metrik kualitas |
| `vibecoding_topics_per_quarter.csv` | Matriks pangsa topik per kuartal |
| `vibecoding_topics_diagnostics.csv` | Skor koherensi dan flag per topik |

---

# Bagian 4 — Timeline

`timeline_analysis.ipynb` menyusun narasi perkembangan dari sisi volume:

1. Tren volume per periode (bulanan dan kuartalan)
2. Pertumbuhan dan kurva adopsi kumulatif
3. Deteksi spike harian sebagai kandidat event
4. Tweet representatif per spike

---

# Troubleshooting

## Grafik Plotly tidak muncul di notebook

Grafik BERTopic (`visualize_barchart`, `visualize_topics`, `visualize_topics_over_time`) memakai Plotly dan bisa **gagal secara senyap** — sel selesai tanpa error, output kosong.

Dua penyebab dan solusinya:

**`nbformat` tidak terpasang.** Plotly membutuhkannya untuk render di notebook, tapi tidak melempar error yang jelas bila tidak ada.

```powershell
pip install nbformat kaleido
```

**Renderer tidak cocok dengan frontend.** Ini yang sering menipu: renderer harus cocok dengan **frontend** (tempat notebook ditampilkan), *bukan* dengan kernel. Kernel Colab yang diakses dari VS Code tetap memerlukan renderer `"notebook"`, bukan `"colab"`, karena JS renderer `"colab"` hanya dipahami frontend Colab.

```python
import plotly.io as pio
pio.renderers.default = "notebook"
fig.show()   # panggil .show() eksplisit; mengembalikan Figure saja tidak selalu ter-render
```

Notebook ini sudah menyediakan helper `show_fig()` yang mencoba renderer `"notebook"` lalu jatuh ke PNG statis via kaleido. Tersedia juga sel fallback matplotlib yang tidak bergantung pada Plotly sama sekali.

## Ukuran file notebook membengkak

Renderer `"notebook"` menyematkan plotly.js (~3 MB) ke **setiap** output sel, sehingga `topic_modeling.ipynb` bisa mencapai belasan MB. Bersihkan output sebelum commit:

```powershell
pip install nbstripout
nbstripout topic_modeling.ipynb
```

Agar otomatis tiap commit:

```powershell
nbstripout --install --attributes .gitattributes
```

## Scraping berhenti sebelum target

Umumnya karena X memang tidak menampilkan cukup post relevan lewat halaman search, bukan karena bug. Perkecil `--chunk-days` dan naikkan `--scrolls-per-window`, atau turunkan `--target-rows`. Hindari melonggarkan filter relevansi dengan keyword tool umum.

---

# Catatan Etika dan Keamanan

- **Jangan commit kredensial.** `.gitignore` sudah menutup `cookies*.json`, `accounts.db`, `*.db`, `sessions/`, dan `.env`. Verifikasi dengan `git ls-files` sebelum push pertama.
- **Dataset mentah tidak disertakan.** `data/raw/*` dikecualikan dari repo karena berisi konten dan identitas pengguna pihak ketiga.
- Ambil data 5 tahun bisa memakan waktu lama karena dibagi menjadi banyak window tanggal. Mulai dari `--limit-per-window 10` atau `50` untuk uji coba.
- Pastikan penggunaan data mengikuti [Terms of Service X](https://x.com/en/tos) dan regulasi perlindungan data yang berlaku. Data ini dikumpulkan untuk keperluan riset.

# Stack

`twscrape` · `playwright` · `pandas` · `transformers` · `torch` · `BERTopic` · `sentence-transformers` · `UMAP` · `HDBSCAN` · `scikit-learn` · `matplotlib` · `seaborn` · `plotly`
