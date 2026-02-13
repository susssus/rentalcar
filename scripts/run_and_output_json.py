#!/usr/bin/env python3
"""
Run the Rentalcars scraper once and print the run as JSON to stdout.
Used by the GitHub Action to POST to the app's /api/ingest.
"""
import json
import logging
import sys
import warnings
from datetime import date, datetime, timezone
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Avoid deprecation warnings on stdout when Action captures 2>&1
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Scrape progress goes to stderr so Action logs show it; JSON stays on stdout
logging.basicConfig(
    level=logging.INFO,
    format="[scraper] %(levelname)s: %(message)s",
    stream=sys.stderr,
    force=True,
)

from scraper import fetch_prices  # noqa: E402
from config import load_config  # noqa: E402

def main():
    cfg = load_config()
    pu, do = cfg["pickup"], cfg["dropoff"]
    pickup_date = f"{pu['year']}-{pu['month']:02d}-{pu['day']:02d}"
    dropoff_date = f"{do['year']}-{do['month']:02d}-{do['day']:02d}"
    rental_days = max(1, (date(do["year"], do["month"], do["day"]) - date(pu["year"], pu["month"], pu["day"])).days)

    try:
        data = fetch_prices(headless=True)
        min_price = data.get("min_price")
        rd = data.get("rental_days", rental_days)
        min_per_day = (min_price / rd) if min_price and rd else None
        run = {
            "run_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "pickup_date": data.get("pickup_date", pickup_date),
            "dropoff_date": data.get("dropoff_date", dropoff_date),
            "rental_days": rd,
            "min_total_price": min_price,
            "min_price_per_day": min_per_day,
            "num_offers": len(data.get("all_prices", [])),
            "url": data.get("url"),
        }
    except Exception as e:
        # Timeout or crash: still output valid JSON so the Action can POST and record that a run was attempted
        run = {
            "run_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "pickup_date": pickup_date,
            "dropoff_date": dropoff_date,
            "rental_days": rental_days,
            "min_total_price": None,
            "min_price_per_day": None,
            "num_offers": 0,
            "url": None,
        }
        print(f"Scraper failed: {e}", file=sys.stderr)
    print(json.dumps(run))
    return 0 if run.get("min_total_price") is not None else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # Last-resort: print minimal valid JSON so workflow doesn't fail on parse
        cfg = load_config()
        pu, do = cfg["pickup"], cfg["dropoff"]
        minimal = {
            "run_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "pickup_date": f"{pu['year']}-{pu['month']:02d}-{pu['day']:02d}",
            "dropoff_date": f"{do['year']}-{do['month']:02d}-{do['day']:02d}",
            "rental_days": 0,
            "min_total_price": None,
            "min_price_per_day": None,
            "num_offers": 0,
            "url": None,
        }
        print(json.dumps(minimal))
        print(str(e), file=sys.stderr)
        sys.exit(2)
