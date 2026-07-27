#!/usr/bin/env python3
"""
setup_env.py — Verifikasi dan bantu setup .env untuk Baubau Deal Finder.

Tidak bertanya apa pun. Hanya melaporkan key mana yang kosong
dan keluar dengan kode 1 selama konfigurasi belum lengkap.

Usage:
    python tools/setup_env.py
"""

import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR.parent / ".env"
EXAMPLE_PATH = BASE_DIR / ".env.example"

# Required keys with descriptions
# Catatan: APIFY_API_TOKEN dihapus, scraping sudah pindah ke Playwright (gratis, tanpa API key).
REQUIRED_KEYS = {
    "SMTP_HOST": "SMTP server (default: smtp.gmail.com)",
    "SMTP_PORT": "SMTP port (default: 587)",
    "SMTP_USER": "Email pengirim",
    "SMTP_PASS": "App password email",
    "NOTIFY_EMAIL": "Email penerima notifikasi",
}


def main():
    if not ENV_PATH.exists():
        print(f"ERROR: .env not found at {ENV_PATH}", file=sys.stderr)
        print(f"Tambahkan key di {EXAMPLE_PATH} ke .env induk, lalu isi nilainya:", file=sys.stderr)
        print(f"  {ENV_PATH}", file=sys.stderr)
        sys.exit(1)
    
    env = {}
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip()
    
    missing = []
    empty = []
    
    for key, desc in REQUIRED_KEYS.items():
        val = env.get(key, "")
        if key not in env:
            missing.append((key, desc))
        elif not val:
            empty.append((key, desc))
    
    if not missing and not empty:
        print("All required keys are set.")
        sys.exit(0)
    
    if missing:
        print("Missing keys (not in .env):")
        for key, desc in missing:
            print(f"  {key} — {desc}")
    
    if empty:
        print("Empty keys (in .env but no value):")
        for key, desc in empty:
            print(f"  {key} — {desc}")
    
    print(f"\nTotal: {len(missing)} missing, {len(empty)} empty")
    sys.exit(1)


if __name__ == "__main__":
    main()
