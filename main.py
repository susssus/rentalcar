#!/usr/bin/env python3
"""
Rentalcars.com price watcher: poll ALC (Alicante), automatic, small cars.
Store history, compute avg/median, notify when price is cheap (below percentile).
"""
import argparse
import logging
import sys
import time
from pathlib import Path

# Run from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_config, build_search_url
from scraper import fetch_prices, dump_page_html
from storage import save_run, get_all_runs
from stats import get_stats, is_cheap
from notify import notify_cheap

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_once(dump_html: bool = False, headless: bool = True) -> dict | None:
    """Fetch prices, save, print stats, notify if cheap. Returns last run data or None."""
    if dump_html:
        dump_page_html()
        return None

    data = fetch_prices(headless=headless)
    if data.get("min_price") is None:
        logger.warning("No prices extracted. Try --dump-html and inspect data/ or page HTML.")
        return None

    cfg = load_config()
    pickup = data["pickup_date"]
    dropoff = data["dropoff_date"]
    rental_days = data["rental_days"]
    min_total = data["min_price"]
    min_per_day = min_total / rental_days

    save_run(data)
    stats = get_stats(pickup, dropoff)

    # Print stats
    print("\n--- Rentalcars ALC (automatic, small) ---")
    print(f"Pickup {pickup} → Dropoff {dropoff} ({rental_days} days)")
    print(f"Current min: €{min_total:.2f} total (€{min_per_day:.2f}/day)")
    print(f"Offers found: {len(data['all_prices'])}")
    if stats["count"] > 0:
        print(f"History: {stats['count']} runs | avg €{stats['avg_per_day']:.2f}/day | median €{stats['median_per_day']:.2f}/day")
        if stats["p25_per_day"] is not None:
            print(f"25th percentile: €{stats['p25_per_day']:.2f}/day (below = cheap)")
    print(f"Search: {data['url']}\n")

    # Notify if cheap
    cheap_pct = cfg.get("cheap_percentile", 0.25)
    cheap, threshold = is_cheap(min_per_day, cheap_pct, pickup, dropoff)
    if cheap and data.get("url"):
        notify_cheap(min_per_day, min_total, rental_days, threshold, data["url"])

    return data


def watch(poll_minutes: int | None = None, headless: bool = True) -> None:
    """Poll every poll_minutes (from config if not set)."""
    cfg = load_config()
    interval = (poll_minutes or cfg.get("poll_interval_minutes", 360)) * 60
    logger.info("Watching every %s minutes", interval // 60)
    while True:
        run_once(headless=headless)
        logger.info("Next run in %s min", interval // 60)
        time.sleep(interval)


def show_stats() -> None:
    """Print stats from stored history (no fetch)."""
    cfg = load_config()
    pickup = f"{cfg['pickup']['year']}-{cfg['pickup']['month']:02d}-{cfg['pickup']['day']:02d}"
    dropoff = f"{cfg['dropoff']['year']}-{cfg['dropoff']['month']:02d}-{cfg['dropoff']['day']:02d}"
    stats = get_stats(pickup, dropoff)
    runs = get_all_runs(pickup, dropoff)
    print("\n--- Stats (ALC, automatic, small) ---")
    print(f"Date range: {pickup} → {dropoff}")
    print(f"Runs recorded: {stats['count']}")
    if stats["count"] > 0:
        print(f"Avg price/day: €{stats['avg_per_day']:.2f}")
        print(f"Median price/day: €{stats['median_per_day']:.2f}")
        print(f"25th percentile (cheap threshold): €{stats['p25_per_day']:.2f}/day")
        print("\nLast 5 runs:")
        for r in runs[-5:]:
            print(f"  {r['run_at']}  €{r['min_price_per_day']:.2f}/day (total €{r['min_total_price']:.2f})")
    else:
        print("No data yet. Run with --once to fetch prices.")
    print()


def main():
    ap = argparse.ArgumentParser(description="Rentalcars ALC price watcher (automatic, small cars)")
    ap.add_argument("--once", action="store_true", help="Run once and exit")
    ap.add_argument("--watch", action="store_true", help="Poll every N minutes (see config)")
    ap.add_argument("--stats", action="store_true", help="Show stats from stored history (no fetch)")
    ap.add_argument("--poll-minutes", type=int, default=None, help="Override poll interval (minutes)")
    ap.add_argument("--dump-html", action="store_true", help="Save search results HTML to file for debugging")
    ap.add_argument("--no-headless", action="store_true", help="Show browser window")
    args = ap.parse_args()

    if args.stats:
        show_stats()
        return
    if args.dump_html:
        run_once(dump_html=True, headless=not args.no_headless)
        return
    if args.watch:
        watch(poll_minutes=args.poll_minutes, headless=not args.no_headless)
        return
    run_once(headless=not args.no_headless)


if __name__ == "__main__":
    main()
