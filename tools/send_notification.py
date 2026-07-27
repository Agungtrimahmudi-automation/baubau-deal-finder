#!/usr/bin/env python3
"""
send_notification.py — Kirim email notifikasi deal menarik.

Usage:
    python tools/send_notification.py --input data/scored_listings.json
    python tools/send_notification.py --input data/scored_listings.json --dry-run
"""

import json
import os
import sys
import argparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime


def load_env():
    """Load .env file from the parent Workflow Automation folder, not the project folder."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


def format_deal_email(listings: list[dict], run_date: str) -> str:
    """Format listings into HTML email body."""
    if not listings:
        return f"""
        <html>
        <body>
        <h2>Baubau Deal Finder — {run_date}</h2>
        <p>Tidak ada deal menarik hari ini.</p>
        </body>
        </html>
        """
    
    great = [l for l in listings if l.get("score_label") == "great_deal"]
    good = [l for l in listings if l.get("score_label") == "good_deal"]
    fair = [l for l in listings if l.get("score_label") == "fair_deal"]
    
    html = f"""
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        h2 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .deal-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 10px 0; }}
        .great {{ border-left: 5px solid #4CAF50; background: #f0fff0; }}
        .good {{ border-left: 5px solid #2196F3; background: #f0f8ff; }}
        .fair {{ border-left: 5px solid #FF9800; background: #fff8f0; }}
        .score {{ font-size: 24px; font-weight: bold; }}
        .great .score {{ color: #4CAF50; }}
        .good .score {{ color: #2196F3; }}
        .fair .score {{ color: #FF9800; }}
        .price {{ color: #e91e63; font-weight: bold; }}
        .savings {{ color: #4CAF50; }}
        .meta {{ color: #666; font-size: 0.9em; }}
    </style>
    </head>
    <body>
    <h2>Baubau Deal Finder — {run_date}</h2>
    <p>Ditemukan <strong>{len(listings)}</strong> deal menarik dari {len(great)} great, {len(good)} good, {len(fair)} fair.</p>
    """
    
    for label, items, emoji in [("Great Deal", great, "🔥"), ("Good Deal", good, "👍"), ("Fair Deal", fair, "💡")]:
        if not items:
            continue
        html += f"<h3>{emoji} {label}</h3>"
        for item in items:
            title = item.get("title", "Tanpa judul")[:80]
            price = item.get("asking_price", 0)
            ref = item.get("reference_price", 0)
            savings = item.get("savings", 0)
            savings_pct = item.get("savings_pct", 0)
            condition = item.get("condition", "unknown")
            cat = item.get("category_name", "-")
            url = item.get("url", item.get("link", "#"))
            group = item.get("group_name", item.get("source", "-"))
            score = item.get("score", 0)
            
            condition_id = {"new": "Baru", "like_new": "Seperti Baru", "used": "Bekas"}.get(condition, condition)
            
            html += f"""
            <div class="deal-card {'great' if score >= 40 else 'good' if score >= 25 else 'fair'}">
                <span class="score">{score:.0f}</span>
                <h4><a href="{url}">{title}</a></h4>
                <p class="price">Rp{price:,.0f} <span style="text-decoration:line-through; color:#999;">Rp{ref:,.0f}</span></p>
                <p class="savings">Hemat Rp{savings:,.0f} ({savings_pct:.0f}% off) — Kondisi: {condition_id}</p>
                <p class="meta">Kategori: {cat} | Grup: {group}</p>
            </div>
            """
    
    html += """
    <hr>
    <p style="color: #999; font-size: 0.8em;">
    Dikirim oleh Baubau Deal Finder | Dari Facebook Groups Baubau
    </p>
    </body>
    </html>
    """
    
    return html


def send_email(subject: str, html_body: str, to_email: str) -> bool:
    """Send email via SMTP."""
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    
    if not smtp_user or not smtp_pass:
        print("ERROR: SMTP_USER and SMTP_PASS must be set in .env", file=sys.stderr)
        return False
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"ERROR sending email: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Send deal notifications via email")
    parser.add_argument("--input", "-i", required=True, help="Path to scored_listings.json")
    parser.add_argument("--dry-run", action="store_true", help="Print email content without sending")
    parser.add_argument("--to", default=None, help="Override recipient email")
    args = parser.parse_args()
    
    load_env()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found", file=sys.stderr)
        sys.exit(1)
    
    with open(input_path, encoding="utf-8") as f:
        listings = json.load(f)
    
    run_date = datetime.now().strftime("%d %B %Y")
    subject = f"Baubau Deal Finder — {len(listings)} deal menarik ditemukan"
    html = format_deal_email(listings, run_date)
    
    if args.dry_run:
        output = Path(input_path).parent / "email_preview.html"
        with open(output, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Dry run — email preview saved to {output}")
        return
    
    to_email = args.to or os.environ.get("NOTIFY_EMAIL", "")
    if not to_email:
        print("ERROR: NOTIFY_EMAIL must be set in .env or use --to", file=sys.stderr)
        sys.exit(1)
    
    success = send_email(subject, html, to_email)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
