# Baubau Deal Finder

Pantau grup Facebook jual beli di Baubau, Sulawesi Tenggara.
Temukan barang baru d harga second — otomatis.

## Masalah

Grup Facebook jual beli Baubau banyak dan data berhamburan. Mau cari deal
tapi males scroll karena noise. Kadang ada barang baru harga second yang
menarik, tapi terlewat karena terlalu banyak listing.

## Solusi

Pipeline otomatis yang:
1. Scrape listing terbaru dari grup Facebook (via Apify)
2. Score setiap listing berdasarkan harga, kondisi, dan indikator scam
3. Kirim email ringkasan hanya deal yang menarik

## Setup

### 1. Daftar Apify (gratis)

1. Buka https://apify.com → Sign up (bisa pakai Google/GitHub)
2. Buka Settings → Integrations → API Token → Copy
3. Token gratis: 10.000 results/bulan

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

# Edit .env — isi token Apify dan SMTP
```

### 4. Edit target grup

Buka `config/groups.json` — ganti/grub Facebook yang mau dipantau.

### 5. Test

```bash
# Dry run (tidak pakai Apify, pakai fixture data)
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
python tools/score_deal.py --input data/raw_listings.json --output data/scored_listings.json
python tools/send_notification.py --input data/scored_listings.json
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
│   ├── scrape_fb_group.py # Scrape via Apify
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

- **Apify free tier:** 10.000 results/bulan, $0
- **Gmail SMTP:** gratis
- **Total:** $0/bulan (sampai free tier habis)

## License

MIT — Copyright (c) 2025 Agung Tri Mahmudi
