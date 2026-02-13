#!/usr/bin/env python3
"""
Run the Rentalcars scraper once and print the run as JSON to stdout.
Used by the GitHub Action to POST to the app's /api/ingest.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper import fetch_prices  # noqa: E402

def main():
    data = fetch_prices(headless=True)
    min_price = data.get("min_price")
    rental_days = data.get("rental_days", 1)
    min_per_day = (min_price / rental_days) if min_price and rental_days else None

    run = {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "pickup_date": data.get("pickup_date", ""),
        "dropoff_date": data.get("dropoff_date", ""),
        "rental_days": rental_days,
        "min_total_price": min_price,
        "min_price_per_day": min_per_day,
        "num_offers": len(data.get("all_prices", [])),
        "url": data.get("url"),
    }
    print(json.dumps(run))
    return 0 if min_price is not None else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(2)
