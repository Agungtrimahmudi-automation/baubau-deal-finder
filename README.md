# Baubau Deal Finder

Pantau grup Facebook jual beli di Baubau, Sulawesi Tenggara.
Temukan barang baru d harga second — otomatis.

**100% GRATIS** — tidak pakai API berbayar. Scraping pakai Playwright.

## Masalah

Grup Facebook jual beli Baubau banyak dan data berhamburan. Mau cari deal
tapi males scroll karena noise. Kadang ada barang baru harga second yang
menarik, tapi terlewat karena terlalu banyak listing.

## Solusi

Pipeline otomatis yang:
1. Scrape listing terbaru dari grup Facebook (via Playwright — gratis)
2. Score setiap listing berdasarkan harga, kondisi, dan indikator scam
3. Kirim email ringkasan hanya deal yang menarik

## Setup

### 1. Install Playwright

```bash
pip install playwright
playwright install chromium
```

### 2. Setup email notification

Butuh SMTP untuk kirim email. Paling gampang pakai Gmail App Password:
1. Buka https://myaccount.google.com/apppasswords
2. Buat app password untuk "Mail"
3. Copy 16 karakter password

### 3. Konfigurasi

```bash
cd "D:\Workflow Automation\Baubau Deal Finder"

# Copy template
cp .env.example .env

# Edit .env — isi SMTP credentials
```

### 4. Edit target grup

Buka `config/groups.json` — ganti/grub Facebook yang mau dipantau.

### 5. Test

```bash
# Dry run (tidak scraping, pakai fixture data)
python tools/run_pipeline.py --dry-run

# Cek hasil
cat data/scored_listings.json
```

## Jalankan

```bash
# Full pipeline
python tools/run_pipeline.py

# Atau stage per stage
python tools/scrape_fb_group.py
python tools/score_deal.py -i data/raw_listings.json -o data/scored_listings.json
python tools/send_notification.py -i data/scored_listings.json
```

## Mode Manual

Kalau scraping gagal atau mau input sendiri:
```bash
python tools/scrape_fb_group.py --manual

# Lalu paste listing:
>> iPhone 14 BNIB|12500000|https://facebook.com/groups/xxx/posts/123
>> Samsung S23 Bekas|8000000|https://facebook.com/groups/xxx/posts/456
>> selesai
```

## Kategori yang Dipantau

- HP / Smartphone
- Laptop / Notebook
- Elektronik (TV, AC, gaming console, dll)
- Kendaraan (motor, mobil)
- Buah & Makanan Segar
- Furniture & Rumah Tangga

Edit `config/categories.json` untuk tambah/ubah kategori.

## Struktur

```
Baubau Deal Finder/
├── config/
│   ├── groups.json        # Grup Facebook target
│   ├── categories.json    # Kategori + harga referensi
│   └── filters.json       # Threshold scoring + scam indicators
├── tools/
│   ├── run_pipeline.py    # Orchestrator (jalankan semua stage)
│   ├── scrape_fb_group.py # Scrape via Playwright (GRATIS)
│   ├── score_deal.py      # Deal scoring engine
│   ├── send_notification.py # Email notifikasi
│   └── setup_env.py       # Verifikasi .env
├── workflows/
│   └── baubau-deal-finder.md
├── data/                  # Hasil scraping + scoring (gitignored)
├── .env                   # Credentials (gitignored)
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Cost

- **Playwright:** gratis (open source)
- **Gmail SMTP:** gratis
- **Total:** $0/bulan selamanya

## License

MIT — Copyright (c) 2025 Agung Tri Mahmudi
