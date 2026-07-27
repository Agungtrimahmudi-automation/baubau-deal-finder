#!/usr/bin/env python3
"""
api.py — HTTP wrapper untuk pipeline Baubau Deal Finder.

n8n jalan di container Docker terpisah dan tidak bisa akses path lokal atau
menjalankan perintah shell di host. Endpoint ini yang dipanggil n8n lewat
node HTTP Request, menggantikan node executeCommand yang tidak bisa jalan.

Usage:
    uvicorn tools.api:app --host 0.0.0.0 --port 8001
"""

import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI()


@app.post("/run")
def run_pipeline(dry_run: bool = False):
    """Jalankan scrape + score, balikin hasilnya langsung di response."""
    args = [sys.executable, str(BASE_DIR / "tools" / "run_pipeline.py"), "--no-notify"]
    if dry_run:
        args.append("--dry-run")

    result = subprocess.run(args, cwd=str(BASE_DIR), capture_output=True, text=True)

    scored_path = BASE_DIR / "data" / "scored_listings.json"
    listings = []
    if scored_path.exists():
        with open(scored_path, encoding="utf-8") as f:
            listings = json.load(f)

    return {
        "exit_code": result.returncode,
        "listings": listings,
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


@app.get("/health")
def health():
    return {"status": "ok"}
