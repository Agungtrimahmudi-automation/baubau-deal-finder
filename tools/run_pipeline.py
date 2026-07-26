#!/usr/bin/env python3
"""
run_pipeline.py — Orchestrator untuk Baubau Deal Finder.

Menjalankan pipeline lengkap: scrape → score → notify.

Usage:
    python tools/run_pipeline.py                    # Full pipeline
    python tools/run_pipeline.py --dry-run          # Dengan fixture data
    python tools/run_pipeline.py --from score       # Mulai dari scoring
    python tools/run_pipeline.py --from notify      # Hanya kirim notifikasi
    python tools/run_pipeline.py --from scrape      # Mulai dari scraping
"""

import json
import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = BASE_DIR / "tools"
DATA_DIR = BASE_DIR / "data"
RUNS_DIR = BASE_DIR / ".tmp" / "runs"


def run_tool(script: str, args: list[str] = None, cwd: str = None) -> int:
    """Run a tool script and return exit code."""
    cmd = [sys.executable, str(TOOLS_DIR / script)] + (args or [])
    print(f"\n{'='*60}")
    print(f"Running: {script} {' '.join(args or [])}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(
        cmd,
        cwd=cwd or str(BASE_DIR),
        capture_output=False
    )
    
    if result.returncode != 0:
        print(f"\nERROR: {script} exited with code {result.returncode}", file=sys.stderr)
    return result.returncode


def create_run_id() -> str:
    """Create a unique run ID."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    parser = argparse.ArgumentParser(description="Baubau Deal Finder pipeline")
    parser.add_argument("--from", dest="start_from", 
                       choices=["scrape", "score", "notify"],
                       default="scrape",
                       help="Start from a specific stage")
    parser.add_argument("--dry-run", action="store_true",
                       help="Use fixture data instead of live scraping")
    parser.add_argument("--no-notify", action="store_true",
                       help="Skip notification (score only)")
    args = parser.parse_args()
    
    run_id = create_run_id()
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'#'*60}")
    print(f"# Baubau Deal Finder — Run {run_id}")
    print(f"# Started: {datetime.now().isoformat()}")
    print(f"# Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"{'#'*60}")
    
    stages = {
        "scrape": {
            "script": "scrape_fb_group.py",
            "args": ["--dry-run"] if args.dry_run else [],
            "output": DATA_DIR / "raw_listings.json",
        },
        "score": {
            "script": "score_deal.py",
            "args": ["--input", str(DATA_DIR / "raw_listings.json"),
                     "--output", str(DATA_DIR / "scored_listings.json")],
            "output": DATA_DIR / "scored_listings.json",
        },
        "notify": {
            "script": "send_notification.py",
            "args": ["--input", str(DATA_DIR / "scored_listings.json")],
            "output": None,
        },
    }
    
    stage_order = ["scrape", "score", "notify"]
    start_idx = stage_order.index(args.start_from)
    
    results = {}
    for stage_name in stage_order[start_idx:]:
        if args.no_notify and stage_name == "notify":
            print(f"\nSkipping {stage_name} (--no-notify)")
            continue
        
        stage = stages[stage_name]
        rc = run_tool(stage["script"], stage["args"])
        results[stage_name] = "OK" if rc == 0 else f"FAILED (code {rc})"
        
        if rc != 0:
            print(f"\nPipeline stopped at {stage_name}")
            break
    
    # Save run log
    log = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "mode": "dry_run" if args.dry_run else "live",
        "start_from": args.start_from,
        "results": results,
    }
    
    log_path = run_dir / "run.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'#'*60}")
    print(f"# Pipeline selesai — Run {run_id}")
    print(f"# Results: {results}")
    print(f"# Log: {log_path}")
    print(f"{'#'*60}")
    
    # Exit with error if any stage failed
    if any("FAILED" in v for v in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
