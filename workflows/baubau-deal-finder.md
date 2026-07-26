# Workflow: Baubau Deal Finder

Pantau grup Facebook jual beli di Baubau dan sekitarnya. Temukan barang baru
d harga second — atau deal menarik lainnya.

## Objective

Dari puluhan listing berhamburan di grup Facebook, keluarin email ringkasan
berisi deal paling menarik yang sudah di-scoring otomatis.

## Pipeline

```
scrape_fb_group.py → score_deal.py → send_notification.py
   (Playwright)       (scoring)        (email SMTP)
```

**100% GRATIS** — tidak pakai API berbayar. Scraping pakai Playwright
(open source browser automation).

## Stages

### 1. Scrape (`tools/scrape_fb_group.py`)

Ambil listing terbaru dari grup Facebook yang sudah didaftarkan di
`config/groups.json`. Pakai Playwright (headless Chromium) — gratis.

**Pertama kali setup:**
```bash
pip install playwright
playwright install chromium
```

**Input:**
- `config/groups.json` — daftar grup URL dan setting scraping

**Output:**
- `data/raw_listings.json` — listing mentah yang baru di-scrape
- `data/all_listings.json` — akumulasi 30 hari terakhir (deduplicated)

**Cara pakai:**
```bash
# Scrape semua grup
python tools/scrape_fb_group.py

# Dry run (fixture data untuk testing)
python tools/scrape_fb_group.py --dry-run

# Scrape satu grup spesifik
python tools/scrape_fb_group.py -g "https://facebook.com/groups/namagrup"

# Input manual (paste listing sendiri)
python tools/scrape_fb_group.py --manual
```

**Mode manual:**
Ketika scraping gagal atau mau input sendiri:
```
>> iPhone 14 BNIB|12500000|https://facebook.com/groups/xxx/posts/123
>> Samsung S23 Bekas|8000000|https://facebook.com/groups/xxx/posts/456
>> selesai
```

**Ketergantungan:**
- Playwright + Chromium (gratis, open source)
- Tidak butuh API key, cookies, atau akun Facebook

### 2. Score (`tools/score_deal.py`)

Hitung skor untuk setiap listing berdasarkan:
- Selisih harga vs harga baru referensi
- Kondisi barang (baru = skor lebih tinggi)
- Indikator scam (penalty)

**Input:**
- `data/raw_listings.json` — hasil scraping
- `config/categories.json` — kategori + harga referensi
- `config/filters.json` — kriteria scoring dan scam

**Output:**
- `data/scored_listings.json` — listing yang sudah di-scoring, sorted by score

**Cara pakai:**
```bash
python tools/score_deal.py --input data/raw_listings.json --output data/scored_listings.json
```

**Scoring Formula:**
```
base_score = (ref_price - asking_price) / ref_price * 100
final_score = base_score * condition_multiplier + scam_score

Labels:
  great_deal = 40+  (🔥)
  good_deal  = 25+  (👍)
  fair_deal  = 10+  (💡)
  skip       = <10
```

### 3. Notify (`tools/send_notification.py`)

Kirim email HTML berisi ringkasan deal menarik.

**Input:**
- `data/scored_listings.json` — hasil scoring
- SMTP credentials dari `.env`

**Output:**
- Email ke `NOTIFY_EMAIL`

**Cara pakai:**
```bash
# Kirim email
python tools/send_notification.py --input data/scored_listings.json

# Dry run (preview HTML, tidak kirim email)
python tools/send_notification.py --input data/scored_listings.json --dry-run
```

### Full Pipeline (`tools/run_pipeline.py`)

Jalankan semua stage sekaligus:

```bash
# Full pipeline
python tools/run_pipeline.py

# Dry run
python tools/run_pipeline.py --dry-run

# Mulai dari scoring (skip scraping)
python tools/run_pipeline.py --from score
```

## Config Reference

### `config/groups.json`
Daftar grup Facebook yang dipantau. Tambah/grup baru di sini.

### `config/categories.json`
Kategori barang + harga referensi baru. Edit untuk tambah kategori atau
adjust harga referensi.

### `config/filters.json`
Threshold scoring dan indikator scam. Edit untuk tuning sensitivity.

## Edge Cases

- **Playwright gagal (Facebook block):** Coba lagi beberapa menit kemudian.
  Atau pakai mode `--manual` untuk input sendiri.
- **Harga tidak terdeteksi:** Listing tanpa harga di-skip otomatis.
- **Kategori tidak match:** Listing tanpa keyword match di-skip.
- **Scam terdeteksi:** Penalty -30 untuk high risk, -5 untuk medium.
- **Duplicate listing:** Dedup by URL. History 30 hari disimpan.

## Scheduling

### Windows Task Scheduler
```
Task: Baubau Deal Finder
Trigger: Daily 07:00 WITA
Action: python D:\Workflow Automation\Baubau Deal Finder\tools\run_pipeline.py
```

### Atau via Hermes cron job
```
Schedule: 0 23 * * *  (23:00 UTC = 07:00 WITA keesokan hari)
```

## Jebakan

- **Facebook mendeteksi Playwright:** Kadang muncul captcha atau blocking.
  **Solusi:** Pakai mode `--manual` sebagai fallback, atau jalankan
  scraping tidak terlalu sering (1-2x sehari maks).
- **Grup privat:** Harus join dulu. Playwright perlu cookies login
  untuk grup privat (belum didukung, untuk versi ini hanya grup publik).
- **Harga referensi perlu update:** Harga barang berubah. Update
  `config/categories.json` secara berkala.
