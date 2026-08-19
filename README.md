# Analisis Diskursus *Vibe Coding* di X/Twitter

Pipeline riset end-to-end untuk memetakan bagaimana istilah *vibe coding* dibicarakan di X/Twitter: dari scraping data, pelabelan sentimen multilingual, sampai topic modeling per kuartal.

Dataset acuan: **~10.000 post relevan**, rentang **Mei 2022 – Juli 2026**, multibahasa (Inggris, Indonesia, Spanyol, Portugis, Jepang, Mandarin).

## 📌 Features

- **Scraping tahan Cloudflare** — scraper Playwright dengan session persisten, plus alternatif `twscrape` berbasis cookie injection
- **Query bertanggal otomatis** — periode panjang dipecah jadi window `since:until` agar hasil search X tidak terpotong limit
- **Filter relevansi ketat** — menjaga konteks inti `vibe coding` dan mencegah kontaminasi keyword tool umum
- **Sentimen multilingual** — XLM-RoBERTa terlatih pada teks Twitter, tanpa perlu deteksi bahasa terpisah
- **Topic modeling per kuartal** — BERTopic dengan pelacakan evolusi topik antar waktu
- **Diagnostik kualitas topik** — skor koherensi otomatis yang menandai klaster tak koheren dan topik *catch-all*
- **Pengaman metodologis** — deteksi kuartal bervolume mikro dan audit reduksi outlier, keduanya mencegah kesimpulan palsu
- **Analisis per tool** — perbandingan sentimen dan topik antar Claude, Cursor, Copilot, Replit, Lovable, Bolt, ChatGPT, Gemini, Windsurf
- **Fallback grafik berlapis** — Plotly interaktif, jatuh ke PNG statis, lalu ke matplotlib murni

## 🛠️ Tech Stack

**Scraping**
- Python 3.12
- Playwright 1.52 — otomasi browser dengan session persisten
- twscrape 0.17 — klien API X alternatif

**NLP & Machine Learning**
- PyTorch 2.12
- Transformers 4.44 — inferensi `cardiffnlp/twitter-xlm-roberta-base-sentiment`
- BERTopic 0.17 — topic modeling
- sentence-transformers 3.0 — embedding `paraphrase-multilingual-MiniLM-L12-v2`
- UMAP 0.5 — reduksi dimensi
- HDBSCAN 0.8 — density-based clustering
- scikit-learn 1.5 — vektorisasi dan c-TF-IDF

**Data & Visualisasi**
- pandas 2.2
- matplotlib 3.10, seaborn 0.13
- Plotly 6.7 + kaleido
- Jupyter / Google Colab

## 📂 Project Structure

```
vibecoding/
├── playwright_scraper.py          # Scraper utama (Playwright, tahan Cloudflare)
├── scraper.py                     # Scraper alternatif (twscrape + cookie injection)
├── label_sentimen.py              # Pelabelan sentimen batch via CLI
│
├── sentiment_colab.ipynb          # Analisis sentimen: distribusi, tren, per tool
├── topic_modeling.ipynb           # BERTopic per kuartal + diagnostik topik
├── timeline_analysis.ipynb        # Volume, kurva adopsi, deteksi spike
├── analysis.ipynb                 # Eksplorasi gabungan & narrative timeline
│
├── requirements.txt               # Dependensi scraping (ringan)
├── requirements-analysis.txt      # Dependensi analisis (berat, termasuk torch)
│
├── data/
│   └── raw/                       # Dataset mentah — TIDAK di-commit
├── sessions/                      # Session browser — TIDAK di-commit
├── cookies.json                   # Kredensial — TIDAK di-commit
└── accounts.db                    # Kredensial — TIDAK di-commit
```

Alur data antar komponen:

```
playwright_scraper.py ─┐
                       ├─→ data/raw/*.csv ─→ label_sentimen.py ─→ sentiment_colab.ipynb
scraper.py ────────────┘                 │
                                         ├─→ topic_modeling.ipynb
                                         └─→ timeline_analysis.ipynb
```

## 🚀 Installation

### Scraping saja

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

### Termasuk analisis

```powershell
pip install -r requirements-analysis.txt
```

Untuk GPU, pasang PyTorch lebih dulu mengikuti [panduan resmi](https://pytorch.org/get-started/locally/), lalu jalankan perintah di atas. Tanpa GPU inferensi tetap jalan, hanya lebih lambat.

### Google Colab

`sentiment_colab.ipynb` dan `topic_modeling.ipynb` bisa dijalankan langsung di Colab tanpa setup lokal — keduanya punya sel instalasi sendiri dan widget upload CSV.

## 💻 Usage

### 1. Login dan scraping

```powershell
python playwright_scraper.py --login
```

Browser terbuka. Login X manual sampai halaman home muncul, kembali ke terminal, tekan `ENTER`. Session tersimpan di `sessions/x_profile`.

Jika Edge bermasalah:

```powershell
python playwright_scraper.py --login --browser-channel chrome
```

Uji coba cepat:

```powershell
python playwright_scraper.py --cookies cookies.json --browser-channel bundled --headless --chunk-days 365 --scrolls-per-window 2 --max-windows 2
```

Dataset penuh 10.000 row:

```powershell
python playwright_scraper.py --cookies cookies.json --browser-channel bundled --headless --chunk-days 30 --scrolls-per-window 25 --delay-ms 1500 --target-rows 10000 --output data/raw/vibecoding_10000.csv
```

> **Jangan longgarkan `--relevant-keywords`** dengan keyword umum seperti `copilot`, `cursor`, `windsurf`, atau `ai coding`. Hasilnya mudah keluar konteks. Bila target tidak tercapai, itu umumnya karena X memang tidak menampilkan cukup post relevan — turunkan target atau perluas periode, jangan longgarkan filter.

### 2. Alternatif: twscrape

Jika login otomatis diblokir Cloudflare, export cookies `x.com` lewat extension seperti **Cookie-Editor** (minimal berisi `auth_token` dan `ct0`), lalu:

```powershell
python scraper.py --inject-cookies-only --username USERNAME_ANDA --cookies cookies_x.json
python scraper.py --query "(vibecoding OR \"vibe coding\")" --limit-per-window 100
```

Login langsung juga tersedia:

```powershell
python scraper.py --login --username USERNAME_ANDA --email EMAIL_ANDA --limit-per-window 50
```

Format akun `twscrape`: `username:password:email:email_password`. Untuk Gmail, `email_password` perlu **App Password**. Jika akun meminta 2FA atau captcha, login otomatis masih bisa gagal.

### 3. Pelabelan sentimen

```powershell
python label_sentimen.py              # baris 1000-2000 (default)
python label_sentimen.py 0 1000       # baris 0-1000
python label_sentimen.py 2000 1000    # baris 2000-3000
```

Input `data/raw/vibecoding_relevant_10000.csv` → output `data/raw/vibecoding_sentimen_{start}_{end}.csv`.

Untuk seluruh dataset sekaligus beserta grafiknya, gunakan `sentiment_colab.ipynb`.

### 4. Topic modeling

Jalankan `topic_modeling.ipynb` berurutan. Parameter utama terkumpul di sel impor:

| Parameter | Default | Efek |
|---|---|---|
| `MIN_TOPIC_SIZE` | `30` | Pengatur granularitas utama; kecil = banyak topik sempit |
| `MIN_SAMPLES` | `10` | Lebih kecil dari `MIN_TOPIC_SIZE` melonggarkan clustering dan menekan outlier |
| `CLUSTER_METHOD` | `"leaf"` | `"leaf"` memecah halus; `"eom"` menghasilkan sedikit klaster besar |
| `NR_TOPICS` | `None` | Reduksi dimatikan — paksaan dapat menggabung topik tak berhubungan |
| `REDUCE_OUTLIERS` | `True` | Menugaskan ulang outlier ke topik terdekat |
| `MIN_QUARTER_DOCS` | `30` | Membuang kuartal bervolume mikro dari analisis tren |
| `COHERENCE_FLOOR` | `0.30` | Batas koherensi untuk menandai topik meragukan |

Keluaran: `vibecoding_topics_docs.csv`, `vibecoding_topics_summary.csv`, `vibecoding_topics_per_quarter.csv`, `vibecoding_topics_diagnostics.csv`.

## 📊 Results

Angka di bawah berasal dari run nyata atas 10.000 post.

### Distribusi sentimen keseluruhan

| Sentimen | Jumlah | Porsi |
|---|---|---|
| Neutral | 5.246 | 52,5% |
| Positive | 2.725 | 27,3% |
| Negative | 2.029 | 20,3% |

Dominasi netral masuk akal: banyak post bersifat berbagi tautan, pengumuman, atau pertanyaan teknis, bukan penilaian.

### Sentimen per tool

Diurutkan berdasarkan *net sentiment* (positif − negatif), hanya tool dengan ≥ 10 sampel:

| Tool | n | Positif | Netral | Negatif | Net |
|---|---|---|---|---|---|
| Lovable | 316 | 39,2% | 48,1% | 12,7% | **+26,5** |
| Replit | 259 | 35,5% | 49,4% | 15,1% | +20,4 |
| Windsurf | 77 | 35,1% | 49,4% | 15,6% | +19,5 |
| Gemini/Google | 325 | 29,8% | 57,2% | 12,9% | +16,9 |
| Bolt | 116 | 26,7% | 62,9% | 10,3% | +16,4 |
| Copilot | 102 | 26,5% | 60,8% | 12,7% | +13,8 |
| ChatGPT/OpenAI | 453 | 27,6% | 58,1% | 14,3% | +13,3 |
| Cursor | 763 | 24,2% | 57,5% | 18,2% | +6,0 |
| Claude | 1.304 | 25,1% | 53,8% | 21,2% | **+3,9** |

Pola yang muncul: tool bervolume pembicaraan **tertinggi** justru bernet sentiment **terendah**. Claude dan Cursor paling banyak dibahas sekaligus paling banyak dikeluhkan — konsisten dengan intensitas pemakaian yang tinggi memunculkan lebih banyak friksi nyata.

### Tren sentimen per kuartal

| Kuartal | Negatif | Netral | Positif |
|---|---|---|---|
| 2025Q1 | 21,4% | 50,4% | 28,2% |
| 2025Q2 | 18,1% | 51,4% | 30,5% |
| 2025Q3 | 19,6% | 49,2% | **31,2%** |
| 2025Q4 | 16,8% | 53,1% | 30,1% |
| 2026Q1 | 21,6% | 53,6% | 24,8% |
| 2026Q2 | 19,7% | 57,3% | 23,1% |
| 2026Q3 | **26,1%** | 53,2% | **20,7%** |

Porsi positif memuncak di 2025Q3 (31,2%) lalu turun ke 20,7% di 2026Q3, sementara negatif naik ke titik tertinggi. Pola ini menyerupai pergeseran dari fase antusiasme awal ke penilaian yang lebih kritis seiring pemakaian produksi.

> Kuartal 2022Q2, 2023Q3, dan 2024Q1 **dikecualikan** — masing-masing hanya berisi 1 post. Lihat [Methodology](#-methodology) untuk alasannya.

### Validasi topik

Cross-tab tool terhadap topik menunjukkan konsentrasi tinggi, indikasi topik menangkap struktur semantik nyata dan bukan derau:

| Tool | Topik dominan | Konsentrasi |
|---|---|---|
| Cursor | `cursor ai_use cursor` | 42,3% |
| Claude | `anthropic_claudecode` | 41,6% |
| Lovable | `billion_revenue_million` | 35,6% |
| Gemini | `gemini pro_flash_gemini cli` | 35,2% |

> **Catatan:** angka topic modeling di atas berasal dari konfigurasi sebelum penyetelan parameter terakhir (`leaf`, `min_samples=10`, reduksi outlier). Jumlah topik dan pangsanya akan berubah setelah notebook dijalankan ulang. Angka sentimen tidak terpengaruh perubahan tersebut.

## 📖 Methodology

### Pengumpulan data

Query difokuskan ke `vibe coding` / `vibecoding` dan dipecah menjadi window `since:until` (default 30 hari) karena halaman search X membatasi jumlah hasil per query. Hasil difilter ulang di sisi klien memakai keyword relevansi agar konteks inti terjaga.

### Preprocessing

Pembersihan dijaga **minimal secara sengaja** — hanya URL dan mention yang dinormalisasi. Emoji dan tanda baca **dipertahankan** karena model sentimen dilatih pada teks Twitter mentah dan kedua elemen itu membawa sinyal. Untuk topic modeling, kata kunci query (`vibe`, `coding`) dimasukkan ke stopword; tanpa itu keduanya mendominasi setiap topik dan menghapus daya bedanya.

Dari 10.000 post, **143 dibuang** (kurang dari 5 kata, duplikat, atau tanpa tanggal valid), menyisakan 9.857 untuk topic modeling.

### Analisis sentimen

Model `cardiffnlp/twitter-xlm-roberta-base-sentiment` dipilih karena multilingual (~8 bahasa terlatih), sehingga korpus campuran bisa diproses tanpa tahap deteksi bahasa dan tanpa model terpisah per bahasa. Inferensi batch 32, panjang maksimum 128 token.

### Topic modeling

Susunan pipeline: **embedding** (`paraphrase-multilingual-MiniLM-L12-v2`) → **UMAP** (5 dimensi, metrik cosine) → **HDBSCAN** → **c-TF-IDF** untuk ekstraksi kata kunci.

`NR_TOPICS` sengaja dimatikan. Reduksi topik paksa dapat **menggabung topik yang tak berhubungan** menjadi klaster sampah — pada run awal, reduksi `"auto"` bahkan tidak mengubah jumlah topik (25 → 25) sehingga hanya menambah risiko tanpa manfaat.

### Diagnostik kualitas topik

Tidak semua klaster bermakna. HDBSCAN dapat menghasilkan klaster "sisa" yang menyatukan dokumen tak berhubungan, dan c-TF-IDF akan tetap memberinya kata kunci yang **tampak** meyakinkan. Dua metrik menyaringnya:

- **Koherensi** — rata-rata cosine similarity dokumen ke centroid topiknya
- **Pangsa** — topik yang menampung porsi berlebihan ditandai sebagai *catch-all*

Topik bertanda `SUSPECT` tidak dipakai menarik kesimpulan tanpa pemeriksaan manual atas sampel dokumennya.

### Dua jebakan metodologis yang ditangani eksplisit

**1. Outlier HDBSCAN bukan sampel acak.**

Yang ditandai outlier justru dokumen paling beragam, yaitu yang berada di wilayah embedding berdensitas rendah. Pada konfigurasi awal, 50% korpus tidak berlabel — artinya setiap persentase yang dihitung dari subset berlabel **tidak bisa digeneralisasi** ke keseluruhan data.

`reduce_outliers()` tidak menghapus baris apa pun; ia hanya mengganti label sehingga cakupan naik mendekati 100%. Trade-off-nya presisi: sebagian dokumen dipaksa masuk topik yang kurang cocok. Kolom `topic_raw` menyimpan penugasan asli agar dampaknya bisa diaudit:

```python
(df["topic_raw"] == -1).mean()                       # porsi yang semula outlier
df[df["topic_raw"] == -1]["topic"].value_counts()     # ke mana mereka pergi
```

**2. Kuartal bervolume mikro menciptakan tren palsu.**

Pada dataset ini, 2022Q2, 2023Q3, dan 2024Q1 masing-masing berisi **tepat 1 post**. Satu dokumen otomatis berarti pangsa 100%. Bila pangsa antar kuartal dirata-ratakan tanpa bobot, kuartal 1 dokumen diperlakukan setara dengan kuartal 2.000 dokumen.

Efeknya terukur: sebuah topik tercatat "turun 18,7 poin persen" padahal seluruh penurunan itu berasal dari **2 post**. Perhitungannya `(0 + 100 + 0 + 0,9 + 1,4) / 5 = 20,5%` untuk paruh awal — didominasi satu kuartal semu.

Dua pengaman dipasang:
- `MIN_QUARTER_DOCS` membuang kuartal bervolume mikro sebelum analisis apa pun
- Pangsa paruh waktu dihitung dari **jumlah dokumen teragregasi**, bukan rata-rata pangsa antar kuartal

### Keterbatasan yang diketahui

- **Ironi dan sarkasme** tetap sulit. *"Vibe coding is amazing until production crashes"* sering terklasifikasi kurang tepat.
- **~25% prediksi berkeyakinan < 0,50.** Untuk klaim kuantitatif yang serius, subset ini perlu ditinjau manual.
- **Potong 128 token** memotong tweet sangat panjang, termasuk yang menyertakan teks kutipan.
- **Bias platform.** Data hanya dari X, dan hanya yang tampil lewat halaman search — bukan sensus lengkap percakapan.
- **Deteksi tool berbasis regex** dapat salah tangkap pada kata ambigu seperti `bolt` atau `cursor` dalam konteks non-tool.

## 🧪 Testing

> **Belum ada test otomatis di repo ini.** Verifikasi saat ini dilakukan lewat sel diagnostik di dalam notebook, bukan lewat test suite. Bagian ini mencatat kondisi sebenarnya sekaligus rencana ke depan, agar tidak menyesatkan.

### Verifikasi yang sudah berjalan

**Diagnostik topik** (sel 6b `topic_modeling.ipynb`) — skor koherensi per topik, deteksi *catch-all* otomatis, dan penandaan `SUSPECT`, disertai cetak sampel dokumen agar bisa dinilai manual.

**Pengaman kuartal** (sel 25) — mencetak jumlah dokumen per kuartal dan melaporkan secara eksplisit kuartal mana yang dibuang beserta alasannya.

**Audit reduksi outlier** (sel 13) — melaporkan tingkat outlier sebelum dan sesudah, serta jumlah dokumen yang ditugaskan ulang.

**Validasi silang tool–topik** — konsentrasi tinggi antara tool dan topik dominannya berfungsi sebagai validasi eksternal bahwa topik bukan derau.

### Validasi struktur notebook

Cek sintaks seluruh sel kode dan urutan definisi variabel:

```powershell
python -c "import ast, json; nb=json.load(open('topic_modeling.ipynb',encoding='utf-8')); [ast.parse(''.join(c['source'])) for c in nb['cells'] if c['cell_type']=='code' and not ''.join(c['source']).lstrip().startswith('%')]; print('OK')"
```

Cek tidak ada kredensial yang ter-track sebelum push:

```powershell
git ls-files | Select-String -Pattern "cookies|accounts|\.db|sessions/"
```

Keluaran harus **kosong**.

### Yang masih perlu dibuat

- Unit test `clean_text()` — penanganan URL, mention, whitespace, input non-string
- Unit test pembagian window tanggal pada scraper
- Test regresi filter relevansi memakai fixture kecil berlabel manual
- Test bahwa `MIN_QUARTER_DOCS` benar-benar membuang kuartal mikro pada data sintetis
- Sanity check konsistensi label model terhadap sampel emas kecil

Kerangka yang disarankan: `pytest`, ditempatkan di `tests/`.

## 🤝 Contributing

Kontribusi dipersilakan. Alur yang diharapkan:

1. Fork repo, lalu buat branch fitur: `git checkout -b fitur/nama-fitur`
2. Terapkan perubahan
3. **Bersihkan output notebook sebelum commit** (lihat catatan di bawah)
4. Commit dengan pesan deskriptif yang menjelaskan *alasan*, bukan hanya *apa*
5. Push dan buka Pull Request

### Wajib: bersihkan output notebook

Renderer Plotly menyematkan plotly.js (~3 MB) ke **setiap** output sel, sehingga notebook bisa membengkak hingga belasan MB dan membebani history git secara permanen.

```powershell
pip install nbstripout
nbstripout --install --attributes .gitattributes   # otomatis tiap commit
```

### Jangan pernah commit

`cookies*.json` · `accounts.db` · `sessions/` · `data/raw/*` · `.env`

Semuanya sudah tercakup `.gitignore`. Verifikasi dengan `git ls-files` sebelum push.

### Troubleshooting umum

**Grafik Plotly kosong tanpa error.** Dua penyebab. Pertama, `nbformat` tidak terpasang — Plotly gagal senyap tanpa pesan jelas: `pip install nbformat kaleido`. Kedua, renderer tidak cocok: renderer harus sesuai dengan **frontend**, *bukan* kernel. Kernel Colab yang diakses dari VS Code tetap butuh renderer `"notebook"`, bukan `"colab"`, karena JS renderer `"colab"` hanya dipahami frontend Colab.

```python
import plotly.io as pio
pio.renderers.default = "notebook"
fig.show()   # panggil .show() eksplisit; mengembalikan Figure saja tidak selalu ter-render
```

Notebook menyediakan helper `show_fig()` dengan fallback berlapis, plus sel fallback matplotlib yang tidak bergantung Plotly sama sekali.

**Scraping berhenti sebelum target.** Umumnya bukan bug — X memang tidak menampilkan cukup post relevan. Perkecil `--chunk-days`, naikkan `--scrolls-per-window`, atau turunkan `--target-rows`.
