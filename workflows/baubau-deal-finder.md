# Workflow: Baubau Deal Finder

Pantau grup Facebook jual beli di Baubau dan sekitarnya. Temukan barang baru
d harga second — atau deal menarik lainnya.

## Objective

Dari puluhan listing berhamburan di grup Facebook, keluarin email ringkasan
berisi deal paling menarik yang sudah di-scoring otomatis.

## Pipeline

```
scrape_fb_group.py → score_deal.py → send_notification.py
     (Apify)         (scoring engine)     (email SMTP)
```

## Stages

### 1. Scrape (`tools/scrape_fb_group.py`)

Ambil listing terbaru dari grup Facebook yang sudah didaftarkan di
`config/groups.json`.

**Input:**
- `config/groups.json` — daftar grup URL dan setting scraping

**Output:**
- `data/raw_listings.json` — listing mentah yang baru di-scrape
- `data/all_listings.json` — akumulasi 30 hari terakhir (deduplicated)

**Cara pakai:**
```bash
# Live scraping
python tools/scrape_fb_group.py

# Dry run (fixture data untuk testing)
python tools/scrape_fb_group.py --dry-run

# Scrape satu grup spesifik
python tools/scrape_fb_group.py --group "https://facebook.com/groups/namagrup"
```

**Ketergantungan:**
- `APIFY_API_TOKEN` di `.env` (gratis: 10.000 results/bulan)
- Free tier Apify: https://apify.com

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
python tools/scrape_fb_group.py --dry-run && python tools/score_deal.py -i data/raw_listings.json
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
# Full pipeline (live)
python tools/run_pipeline.py

# Dry run
python tools/run_pipeline.py --dry-run

# Mulai dari scoring (skip scraping)
python tools/run_pipeline.py --from score

# Hanya kirim notifikasi
python tools/run_pipeline.py --from notify --no-notify
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

- **Scrape gagal (timeout/blocked):** Coba lagi 5 menit kemudian. Apify
  free tier tidak membatasi retry, tapi ada concurrent run limit 1.
- **Harga tidak terdeteksi:** Listing tanpa harga di-skip otomatis.
- **Kategori tidak match:** Listing tanpa keyword match di-skip.
- **Scam terdeteksi:** Penalty -30 untuk high risk, -5 untuk medium.
  Jika masih positif setelah penalty, tetap masuk tapi dengan label rendah.
- **Duplicate listing:** Dedup by URL. History 30 hari disimpan di
  `data/all_listings.json`.

## Scheduling

### Windows Task Scheduler
```
Task: Baubau Deal Finder
Trigger: Daily 07:00 WITA
Action: python D:\Workflow Automation\Baubau Deal Finder\tools\run_pipeline.py
```

### Atau via Hermes cron job
```
Schedule: 0 7 * * *  (07:00 WITA = 23:00 UTC previous day)
```

## Jebakan

- **Apify free tier:** 10.000 results/bulan. Satu grup ~50 posts = ~300
  results per hari. Pakai 6 grup = 1.800/hari = 54.000/bulan. OVER LIMIT.
  **Solusi:** Batasi max_posts_per_group atau pantau fewer groups.
- **Facebook memblokir scraping:** Apify handle ini, tapi kadang perlu
  refresh cookies. Cek dashboard Apify jika run gagal.
- **Harga referensi perlu update:** Harga barang berubah. Update
  `config/categories.json` secara berkala.
