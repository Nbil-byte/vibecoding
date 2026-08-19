# Vibecoding X Scraper

Project minimal untuk mengambil data X memakai `twscrape` dan menyimpan hasil ke CSV. Fokus project ini hanya pengambilan data.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

## Alternatif Login Manual dengan Playwright

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

## Login Akun X

`twscrape` tidak bisa login memakai Google API. Jika akun X dibuat dengan "Sign in with Google", tetap perlu password akun X atau setup login X yang bisa dipakai langsung.

Format login yang dipakai `twscrape` adalah:

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

Pastikan cookies yang diexport berisi minimal:

- `auth_token`
- `ct0`

Simpan file cookies di project, misalnya:

```text
cookies_x.json
```

Lalu inject ke akun `twscrape`:

```powershell
python scraper.py --inject-cookies-only --username USERNAME_ANDA --cookies cookies_x.json
```

Setelah status akun aktif, jalankan scraping:

```powershell
python scraper.py --query "(vibecoding OR \"vibe coding\" OR \"AI coding\" OR \"ngoding pakai AI\" OR \"kode pakai AI\")" --limit-per-window 100
```

File `cookies*.json` sudah masuk `.gitignore`, jadi jangan commit file cookies.

## Scraping Data 5 Tahun Belakang

Setelah login berhasil:

```powershell
python scraper.py --query "(vibecoding OR \"vibe coding\" OR \"AI coding\" OR \"ngoding pakai AI\" OR \"kode pakai AI\")" --limit-per-window 100
```

Script otomatis membuat query bertanggal selama 5 tahun terakhir memakai filter:

```text
since:YYYY-MM-DD until:YYYY-MM-DD
```

Default rentang per batch adalah 30 hari. Ubah jika perlu:

```powershell
python scraper.py --chunk-days 7 --limit-per-window 50
```

## Output

Default output:

```text
data/raw/tweets_vibecoding_5y_YYYYMMDD_HHMMSS.csv
```

Tentukan output manual:

```powershell
python scraper.py --output data/raw/vibecoding.csv
```

## Kolom CSV

- `tweet_id`
- `created_at`
- `text`
- `author_id`
- `username`
- `displayname`
- `lang`
- `like_count`
- `retweet_count`
- `reply_count`
- `quote_count`
- `view_count`
- `url`
- `search_query`
- `since`
- `until`

## Catatan

- Ambil data 5 tahun bisa memakan waktu lama karena dibagi menjadi banyak window tanggal.
- Mulai dari `--limit-per-window 10` atau `50` untuk uji coba.
- Pastikan penggunaan data mengikuti aturan platform X.
