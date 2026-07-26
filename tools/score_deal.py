#!/usr/bin/env python3
"""
score_deal.py — Deal scoring engine untuk Baubau Deal Finder.

Menghitung skor untuk setiap listing berdasarkan:
1. Selisih harga vs referensi baru
2. Kondisi barang (baru = skor lebih tinggi)
3. Indikator scam (penalty)

Usage:
    python tools/score_deal.py --input data/raw_listings.json --output data/scored_listings.json
    python tools/score_deal.py --input data/raw_listings.json  # print ke stdout
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


def load_config(name: str) -> dict:
    path = CONFIG_DIR / name
    if not path.exists():
        print(f"ERROR: config/{name} not found", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_price(text: str) -> int | None:
    """Extract price from text like 'Rp 1.500.000' or '1500000' or '1,5jt'."""
    if not text:
        return None
    
    text = text.lower().strip()
    
    # Handle shorthand: 1,5jt, 2jt, 500rb, 100rb
    jt_match = re.search(r'(\d+[.,]?\d*)\s*jt', text)
    if jt_match:
        val = float(jt_match.group(1).replace(',', '.'))
        return int(val * 1_000_000)
    
    rb_match = re.search(r'(\d+[.,]?\d*)\s*rb', text)
    if rb_match:
        val = float(rb_match.group(1).replace(',', '.'))
        return int(val * 1_000)
    
    # Standard format: Rp 1.500.000 or 1.500.000
    rp_match = re.search(r'rp\.?\s*([\d.,]+)', text)
    if rp_match:
        num_str = rp_match.group(1).replace('.', '').replace(',', '')
        try:
            return int(num_str)
        except ValueError:
            return None
    
    # Plain number
    plain_match = re.search(r'([\d]{3,})', text.replace('.', '').replace(',', ''))
    if plain_match:
        return int(plain_match.group(1))
    
    return None


def detect_condition(text: str, category: dict) -> str:
    """Detect item condition from listing text."""
    text_lower = text.lower()
    condition_kw = category.get("condition_keywords", {})
    
    # Check new first (highest priority)
    for kw in condition_kw.get("new", []):
        if kw.lower() in text_lower:
            return "new"
    
    # Then like_new
    for kw in condition_kw.get("like_new", []):
        if kw.lower() in text_lower:
            return "like_new"
    
    # Then used
    for kw in condition_kw.get("used", []):
        if kw.lower() in text_lower:
            return "used"
    
    # Check fresh for food
    for kw in condition_kw.get("fresh", []):
        if kw.lower() in text_lower:
            return "new"
    
    return "unknown"


def match_category(text: str, categories: list[dict]) -> dict | None:
    """Match listing text to a category."""
    text_lower = text.lower()
    best_match = None
    best_score = 0
    
    for cat in categories:
        score = 0
        for kw in cat.get("keywords", []):
            if kw.lower() in text_lower:
                score += 1
        if score > best_score:
            best_score = score
            best_match = cat
    
    return best_match if best_score > 0 else None


def get_reference_price(price: int, category: dict) -> int | None:
    """Get reference new price based on asking price and category ranges."""
    for range_name, range_data in category.get("price_ranges", {}).items():
        if range_data["min"] <= price <= range_data["max"]:
            return range_data["ref_new"]
    
    # If no range matches, use the highest ref price
    refs = [r["ref_new"] for r in category.get("price_ranges", {}).values()]
    return max(refs) if refs else None


def score_scam(text: str, filters: dict) -> int:
    """Calculate scam penalty score."""
    text_lower = text.lower()
    scam = filters.get("scam_indicators", {})
    scoring = scam.get("scoring", {})
    
    penalty = 0
    
    for pattern in scam.get("high_risk_patterns", []):
        if pattern.lower() in text_lower:
            penalty += scoring.get("high_risk", -30)
    
    for pattern in scam.get("medium_risk_patterns", []):
        if pattern.lower() in text_lower:
            penalty += scoring.get("medium_risk", -5)
    
    for pattern in scam.get("low_risk_patterns", []):
        if pattern.lower() in text_lower:
            penalty += scoring.get("low_risk", 10)
    
    return penalty


def score_listing(listing: dict, categories: list[dict], filters: dict) -> dict:
    """Score a single listing."""
    text = f"{listing.get('title', '')} {listing.get('description', '')}"
    
    # Match category
    category = match_category(text, categories)
    if not category:
        return {
            **listing,
            "score": 0,
            "score_label": "skip",
            "category": None,
            "condition": "unknown",
            "reason": "no category match"
        }
    
    # Extract price
    price_text = listing.get("price", "") or listing.get("title", "")
    price = extract_price(price_text)
    if not price:
        return {
            **listing,
            "score": 0,
            "score_label": "skip",
            "category": category["id"],
            "condition": "unknown",
            "reason": "no price detected"
        }
    
    # Get reference price
    ref_price = get_reference_price(price, category)
    if not ref_price:
        return {
            **listing,
            "score": 0,
            "score_label": "skip",
            "category": category["id"],
            "condition": "unknown",
            "reason": "no reference price"
        }
    
    # Detect condition
    condition = detect_condition(text, category)
    
    # Base deal score
    if ref_price > 0:
        base_score = (ref_price - price) / ref_price * 100
    else:
        base_score = 0
    
    # Condition multiplier
    multipliers = filters.get("deal_scoring", {}).get("condition_multiplier", {})
    multiplier = multipliers.get(condition, 0.8)
    
    # Final score
    final_score = base_score * multiplier + score_scam(text, filters)
    final_score = max(0, min(100, final_score))
    
    # Score label
    thresholds = filters.get("deal_scoring", {}).get("thresholds", {})
    if final_score >= thresholds.get("great_deal", 40):
        label = "great_deal"
    elif final_score >= thresholds.get("good_deal", 25):
        label = "good_deal"
    elif final_score >= thresholds.get("fair_deal", 10):
        label = "fair_deal"
    else:
        label = "skip"
    
    savings = ref_price - price
    savings_pct = (savings / ref_price * 100) if ref_price > 0 else 0
    
    return {
        **listing,
        "score": round(final_score, 1),
        "score_label": label,
        "category": category["id"],
        "category_name": category["name"],
        "condition": condition,
        "asking_price": price,
        "reference_price": ref_price,
        "savings": savings,
        "savings_pct": round(savings_pct, 1),
        "reason": f"deal: Rp{savings:,.0f} below new price ({condition})"
    }


def main():
    parser = argparse.ArgumentParser(description="Score Facebook marketplace listings")
    parser.add_argument("--input", "-i", required=True, help="Path to raw_listings.json")
    parser.add_argument("--output", "-o", default=None, help="Path to output scored_listings.json")
    parser.add_argument("--min-score", type=float, default=None, help="Minimum score to include")
    args = parser.parse_args()
    
    # Load configs
    categories = load_config("categories.json").get("categories", [])
    filters = load_config("filters.json")
    
    # Load listings
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found", file=sys.stderr)
        sys.exit(1)
    
    with open(input_path, encoding="utf-8") as f:
        listings = json.load(f)
    
    if not isinstance(listings, list):
        print("ERROR: input must be a JSON array of listings", file=sys.stderr)
        sys.exit(1)
    
    # Score all listings
    scored = [score_listing(lst, categories, filters) for lst in listings]
    
    # Filter by minimum score
    min_score = args.min_score or filters.get("minimum_score", 0)
    scored = [s for s in scored if s["score"] >= min_score]
    
    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    # Limit results
    max_results = filters.get("maximum_results_per_run", 20)
    scored = scored[:max_results]
    
    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(scored, f, indent=2, ensure_ascii=False)
        print(f"Scored {len(scored)} listings to {output_path}")
    else:
        print(json.dumps(scored, indent=2, ensure_ascii=False))
    
    # Summary
    great = sum(1 for s in scored if s["score_label"] == "great_deal")
    good = sum(1 for s in scored if s["score_label"] == "good_deal")
    fair = sum(1 for s in scored if s["score_label"] == "fair_deal")
    print(f"\nSummary: {great} great, {good} good, {fair} fair deals found", file=sys.stderr)


if __name__ == "__main__":
    main()
