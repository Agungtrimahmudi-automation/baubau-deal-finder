#!/usr/bin/env python3
"""
scrape_fb_group.py — Scrape Facebook groups via Playwright (100% GRATIS).

Tidak pakai API berbayar. Playwright buka browser langsung, scroll, ambil data.

Usage:
    python tools/scrape_fb_group.py                    # Scrape semua grup di config
    python tools/scrape_fb_group.py -g "URL_GRUP"     # Scrape satu grup
    python tools/scrape_fb_group.py --dry-run          # Test dengan fixture data
    python tools/scrape_fb_group.py --manual           # Input manual dari stdin

Pertama kali jalankan, install Playwright dulu:
    pip install playwright
    playwright install chromium
"""

import json
import os
import sys
import re
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"


def load_config(name: str) -> dict:
    path = CONFIG_DIR / name
    if not path.exists():
        print(f"ERROR: config/{name} not found", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_price(text: str) -> str:
    """Coba ekstrak harga dari teks listing."""
    if not text:
        return ""
    # Cari pola harga: Rp 1.500.000, 1500000, 1,5jt, 500rb
    patterns = [
        r'rp\.?\s*[\d.,]+',
        r'\d+[.,]\d+\s*jt',
        r'\d+\s*jt',
        r'\d+\s*rb',
        r'rp\s*\d+',
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return ""


def scrape_with_playwright(group_url: str, max_posts: int = 30) -> list[dict]:
    """Scrape Facebook group using Playwright (headless browser)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright belum terinstall.", file=sys.stderr)
        print("Jalankan:", file=sys.stderr)
        print("  pip install playwright", file=sys.stderr)
        print("  playwright install chromium", file=sys.stderr)
        sys.exit(1)
    
    listings = []
    print(f"  Membuka: {group_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="id-ID",
        )
        page = context.new_page()
        
        try:
            page.goto(group_url, wait_until="networkidle", timeout=30000)
            time.sleep(3)  # Tunggu konten load
            
            # Scroll untuk load lebih banyak post
            for i in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
            
            # Ambil semua post/kartu listing
            # Facebook groups biasanya pakai div dengan role="article" atau post container
            posts = page.query_selector_all('[role="article"]')
            
            if not posts:
                # Fallback: coba selector lain
                posts = page.query_selector_all('div[data-ad-rendering-role="story_message"]')
            
            if not posts:
                # Fallback: ambil semua link post
                posts = page.query_selector_all('a[href*="/posts/"]')
            
            print(f"  Ditemukan {len(posts)} elemen post")
            
            for post in posts[:max_posts]:
                try:
                    # Ambil teks
                    text = post.inner_text()
                    
                    # Ambil link
                    link_el = post.query_selector('a[href*="/posts/"]')
                    url = link_el.get_attribute('href') if link_el else ""
                    if url and not url.startswith("http"):
                        url = "https://www.facebook.com" + url
                    
                    # Ambil judul (baris pertama yang cukup pendek)
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    title = lines[0] if lines else text[:100]
                    
                    # Ambil deskripsi (gabung beberapa baris)
                    description = ' '.join(lines[1:5]) if len(lines) > 1 else ""
                    
                    # Ekstrak harga
                    price = extract_price(text)
                    
                    if title and len(title) > 5:  # Skip post kosong
                        listings.append({
                            "title": title[:200],
                            "description": description[:500],
                            "price": price,
                            "url": url,
                            "group_name": group_url,
                            "source": "facebook",
                            "scraped_at": datetime.now().isoformat(),
                            "raw_text": text[:1000],
                        })
                except Exception as e:
                    continue  # Skip post yang gagal di-parse
            
        except Exception as e:
            print(f"  ERROR scraping: {e}", file=sys.stderr)
        finally:
            browser.close()
    
    print(f"  Berhasil ambil {len(listings)} listing")
    return listings


def manual_input() -> list[dict]:
    """Input manual — user paste listing satu per satu."""
    print("\n=== MODE MANUAL INPUT ===")
    print("Paste listing Facebook satu per satu.")
    print("Format: judul|harga|link (pisah dengan |)")
    print("Contoh: iPhone 14 BNIB|12500000|https://facebook.com/groups/xxx/posts/123")
    print("Ketik 'selesai' untuk finish.\n")
    
    listings = []
    while True:
        try:
            line = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if line.lower() in ("selesai", "done", "quit", "q", ""):
            if not listings:
                print("Belum ada listing.")
                continue
            break
        
        parts = line.split("|")
        if len(parts) < 2:
            print("  Format: judul|harga|link")
            continue
        
        title = parts[0].strip()
        price = parts[1].strip()
        url = parts[2].strip() if len(parts) > 2 else ""
        
        listings.append({
            "title": title,
            "description": "",
            "price": price,
            "url": url,
            "group_name": "Manual Input",
            "source": "manual",
            "scraped_at": datetime.now().isoformat(),
        })
        print(f"  Ditambahkan: {title[:50]}")
    
    return listings


def load_fixture() -> list[dict]:
    """Load fixture data untuk testing offline."""
    fixture_path = DATA_DIR / "fixture_listings.json"
    if fixture_path.exists():
        with open(fixture_path, encoding="utf-8") as f:
            return json.load(f)
    
    # Buat fixture data
    listings = [
        {
            "title": "iPhone 14 Pro Max 256GB BNIB Garansi Resmi",
            "description": "Brand new in box, garansi resmi iBox 1 tahun. Masih segel.",
            "price": "Rp 12.500.000",
            "url": "https://facebook.com/groups/jualbelibaubau/posts/12345",
            "group_name": "Jual Beli Baubau",
            "source": "facebook"
        },
        {
            "title": "Samsung Galaxy S23 Ultra Bekas Mulus",
            "description": "Dijual cepat, kondisi 95% mulus. Bisa COD Baubau.",
            "price": "Rp 8.000.000",
            "url": "https://facebook.com/groups/jualbelibaubau/posts/12346",
            "group_name": "Jual Beli Baubau",
            "source": "facebook"
        },
        {
            "title": "iPhone 14 Pro Max 128GB",
            "description": "Transfer dulu baru dikirim. No COD. WA only.",
            "price": "Rp 5.000.000",
            "url": "https://facebook.com/groups/jualbelibaubau/posts/12347",
            "group_name": "Jual Beli Baubau",
            "source": "facebook"
        },
        {
            "title": "Xiaomi Redmi Note 12 4/128GB",
            "description": "Baru dipakai 2 bulan, masih garansi. Seperti baru.",
            "price": "Rp 1.200.000",
            "url": "https://facebook.com/groups/jualbelibaubau/posts/12348",
            "group_name": "Jual Beli Baubau",
            "source": "facebook"
        },
        {
            "title": "Durian Montong Segar Panen Kebun Sendiri",
            "description": "Baru petik, manis legit. Harga Rp 35.000/kg.",
            "price": "Rp 35.000",
            "url": "https://facebook.com/groups/jualbelibaubau/posts/12349",
            "group_name": "Jual Beli Baubau",
            "source": "facebook"
        },
        {
            "title": "Laptop ASUS VivoBook 14 i5-12th Gen",
            "description": "Jarang pakai, masih mulus. COD Baubau.",
            "price": "Rp 4.500.000",
            "url": "https://facebook.com/groups/jualbelibaubau/posts/12350",
            "group_name": "Jual Beli Baubau",
            "source": "facebook"
        },
        {
            "title": "Honda Beat Street 2023",
            "description": "Low km, terawat, service record lengkap.",
            "price": "Rp 14.000.000",
            "url": "https://facebook.com/groups/jualbelibaubau/posts/12351",
            "group_name": "Jual Beli Baubau",
            "source": "facebook"
        },
        {
            "title": "PS5 Disk Edition Garansi Resmi",
            "description": "Baru sebulan, masih segel box. Garansi Sony.",
            "price": "Rp 4.000.000",
            "url": "https://facebook.com/groups/jualbelibaubau/posts/12352",
            "group_name": "Jual Beli Baubau",
            "source": "facebook"
        }
    ]
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(fixture_path, "w", encoding="utf-8") as f:
        json.dump(listings, f, indent=2, ensure_ascii=False)
    
    return listings


def load_existing() -> list[dict]:
    """Load listing yang sudah ada (dedup)."""
    existing_path = DATA_DIR / "all_listings.json"
    if existing_path.exists():
        with open(existing_path, encoding="utf-8") as f:
            return json.load(f)
    return []


def deduplicate(new_listings: list[dict], existing: list[dict]) -> list[dict]:
    """Hapus duplikat berdasarkan URL."""
    existing_urls = {l.get("url") for l in existing if l.get("url")}
    unique = []
    for lst in new_listings:
        url = lst.get("url", "")
        if url and url not in existing_urls:
            unique.append(lst)
            existing_urls.add(url)
        elif not url:
            unique.append(lst)  # Tanpa URL tetap dimasukkan
    return unique


def main():
    parser = argparse.ArgumentParser(description="Scrape Facebook groups (GRATIS via Playwright)")
    parser.add_argument("--group", "-g", help="Scrape satu grup spesifik")
    parser.add_argument("--dry-run", action="store_true", help="Pakai fixture data (testing)")
    parser.add_argument("--manual", action="store_true", help="Input manual dari stdin")
    parser.add_argument("--output", "-o", default=None, help="Output path")
    args = parser.parse_args()
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.dry_run:
        listings = load_fixture()
        print(f"Dry run — {len(listings)} fixture listing")
    elif args.manual:
        listings = manual_input()
    else:
        groups_config = load_config("groups.json")
        settings = groups_config.get("scrape_settings", {})
        max_posts = settings.get("max_posts_per_group", 30)
        
        all_listings = []
        
        if args.group:
            groups = [{"name": "Manual", "url": args.group}]
        else:
            groups = groups_config.get("groups", [])
        
        for group in groups:
            url = group.get("url", "")
            name = group.get("name", "Unknown")
            if not url:
                continue
            
            print(f"\nScraping: {name}")
            items = scrape_with_playwright(url, max_posts)
            
            # Tambahkan group_name
            for item in items:
                if item.get("group_name") == url:
                    item["group_name"] = name
            
            all_listings.extend(items)
        
        # Dedup
        existing = load_existing()
        new_listings = deduplicate(all_listings, existing)
        listings = new_listings
        
        # Update all_listings
        all_combined = existing + new_listings
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        all_combined = [l for l in all_combined if l.get("scraped_at", "") >= cutoff]
        
        with open(DATA_DIR / "all_listings.json", "w", encoding="utf-8") as f:
            json.dump(all_combined, f, indent=2, ensure_ascii=False)
        
        print(f"\nTotal: {len(new_listings)} baru (dari {len(all_listings)} scraped)")
    
    # Simpan
    output_path = Path(args.output) if args.output else DATA_DIR / "raw_listings.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(listings, f, indent=2, ensure_ascii=False)
    
    print(f"Tersimpan ke {output_path}")


if __name__ == "__main__":
    main()
