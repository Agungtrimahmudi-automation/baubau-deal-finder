#!/usr/bin/env python3
"""
scrape_fb_group.py — Scrape Facebook groups via Apify API.

Apify Actor: apify/facebook-group-scraper
Free tier: 10.000 results/bulan

Usage:
    python tools/scrape_fb_group.py
    python tools/scrape_fb_group.py --group "https://facebook.com/groups/jualbelibaubau"
    python tools/scrape_fb_group.py --dry-run  # test dengan fixture data
"""

import json
import os
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timedelta


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"


def load_env():
    """Load .env file."""
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


def load_config(name: str) -> dict:
    path = CONFIG_DIR / name
    if not path.exists():
        print(f"ERROR: config/{name} not found", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def apify_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make a request to Apify API."""
    token = os.environ.get("APIFY_API_TOKEN", "")
    if not token:
        print("ERROR: APIFY_API_TOKEN must be set in .env", file=sys.stderr)
        sys.exit(1)
    
    url = f"https://api.apify.com/v2{endpoint}"
    if "?" in url:
        url += f"&token={token}"
    else:
        url += f"?token={token}"
    
    headers = {"Content-Type": "application/json"}
    
    if data:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"Apify API error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)


def scrape_group(group_url: str, settings: dict) -> list[dict]:
    """Scrape a single Facebook group using Apify."""
    print(f"Scraping: {group_url}")
    
    actor_input = {
        "startUrls": [{"url": group_url}],
        "maxPosts": settings.get("max_posts_per_group", 50),
        "sorting": settings.get("sort_by", "newest"),
        "includeComments": settings.get("include_comments", False),
    }
    
    # Start the actor run
    result = apify_request("POST", "/acts/apify~facebook-group-scraper/runs", actor_input)
    run_id = result["data"]["id"]
    print(f"  Run started: {run_id}")
    
    # Poll until complete (max 5 minutes)
    max_wait = 300
    poll_interval = 5
    elapsed = 0
    
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        
        status_result = apify_request("GET", f"/actor-runs/{run_id}")
        status = status_result["data"]["status"]
        
        if status == "SUCCEEDED":
            break
        elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
            print(f"  Run {status}: {status_result['data'].get('statusMessage', '')}", file=sys.stderr)
            return []
        else:
            print(f"  Status: {status} ({elapsed}s)")
    
    if elapsed >= max_wait:
        print(f"  Run timed out after {max_wait}s", file=sys.stderr)
        return []
    
    # Get dataset items
    dataset_id = status_result["data"]["defaultDatasetId"]
    items_result = apify_request("GET", f"/datasets/{dataset_id}/items?format=json")
    
    items = items_result if isinstance(items_result, list) else items_result.get("data", [])
    print(f"  Got {len(items)} items")
    return items


def normalize_listing(item: dict, group_name: str) -> dict:
    """Normalize Apify output to our standard format."""
    return {
        "title": item.get("title", item.get("name", "")),
        "description": item.get("description", item.get("text", "")),
        "price": item.get("price", item.get("formattedPrice", "")),
        "url": item.get("url", item.get("postUrl", item.get("link", ""))),
        "image_url": item.get("image", item.get("imageUrl", item.get("images", [""])[0] if item.get("images") else "")),
        "seller_name": item.get("sellerName", item.get("author", "")),
        "posted_date": item.get("time", item.get("postedAt", item.get("date", ""))),
        "group_name": group_name,
        "source": "facebook",
        "scraped_at": datetime.now().isoformat(),
        "raw": item,
    }


def load_existing_listings() -> list[dict]:
    """Load previously scraped listings to avoid duplicates."""
    existing_path = DATA_DIR / "all_listings.json"
    if existing_path.exists():
        with open(existing_path, encoding="utf-8") as f:
            return json.load(f)
    return []


def deduplicate_listings(listings: list[dict], existing: list[dict]) -> list[dict]:
    """Remove duplicates based on URL."""
    existing_urls = {l.get("url") for l in existing if l.get("url")}
    new_listings = []
    for lst in listings:
        url = lst.get("url", "")
        if url and url not in existing_urls:
            new_listings.append(lst)
            existing_urls.add(url)
    return new_listings


def main():
    parser = argparse.ArgumentParser(description="Scrape Facebook groups via Apify")
    parser.add_argument("--group", "-g", help="Scrape a specific group URL")
    parser.add_argument("--dry-run", action="store_true", help="Use fixture data instead of live scraping")
    parser.add_argument("--output", "-o", default=None, help="Output path for raw listings")
    args = parser.parse_args()
    
    if args.dry_run:
        # Generate fixture data for testing
        fixture_path = DATA_DIR / "fixture_listings.json"
        if fixture_path.exists():
            with open(fixture_path, encoding="utf-8") as f:
                listings = json.load(f)
        else:
            print("Creating fixture data for offline testing...", file=sys.stderr)
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
        
        output_path = Path(args.output) if args.output else DATA_DIR / "raw_listings.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(listings, f, indent=2, ensure_ascii=False)
        print(f"Dry run — {len(listings)} fixture listings saved to {output_path}")
        return
    
    # Live scraping
    load_env()
    
    groups_config = load_config("groups.json")
    settings = groups_config.get("scrape_settings", {})
    
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
        
        items = scrape_group(url, settings)
        normalized = [normalize_listing(item, name) for item in items]
        all_listings.extend(normalized)
    
    # Deduplicate against existing
    existing = load_existing_listings()
    new_listings = deduplicate_listings(all_listings, existing)
    
    # Save raw listings
    output_path = Path(args.output) if args.output else DATA_DIR / "raw_listings.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(new_listings, f, indent=2, ensure_ascii=False)
    
    # Update all_listings
    all_combined = existing + new_listings
    # Keep only last 30 days
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    all_combined = [l for l in all_combined if l.get("scraped_at", "") >= cutoff]
    
    with open(DATA_DIR / "all_listings.json", "w", encoding="utf-8") as f:
        json.dump(all_combined, f, indent=2, ensure_ascii=False)
    
    print(f"\nTotal: {len(new_listings)} new listings (from {len(all_listings)} scraped)")
    print(f"Saved to {output_path}")
    print(f"Full history: {len(all_combined)} listings in all_listings.json")


if __name__ == "__main__":
    main()
