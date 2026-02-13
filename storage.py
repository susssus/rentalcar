"""
SQLite storage for price history. Tracks each poll run and min price per day.
"""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "data" / "prices.db"


def _ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT NOT NULL,
            pickup_date TEXT NOT NULL,
            dropoff_date TEXT NOT NULL,
            rental_days INTEGER NOT NULL,
            min_total_price REAL,
            min_price_per_day REAL,
            num_offers INTEGER,
            url TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_run(data: dict) -> int:
    """Save one poll result. Returns run id."""
    _ensure_db()
    min_price = data.get("min_price")
    rental_days = data.get("rental_days", 1)
    min_per_day = (min_price / rental_days) if min_price and rental_days else None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """
        INSERT INTO runs (run_at, pickup_date, dropoff_date, rental_days, min_total_price, min_price_per_day, num_offers, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat() + "Z",
            data.get("pickup_date", ""),
            data.get("dropoff_date", ""),
            rental_days,
            min_price,
            min_per_day,
            len(data.get("all_prices", [])),
            data.get("url"),
        ),
    )
    run_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info("Saved run id=%s min_total=%.2f min_per_day=%.2f", run_id, min_price or 0, min_per_day or 0)
    return run_id


def get_all_runs(pickup_date: str | None = None, dropoff_date: str | None = None):
    """Get all runs, optionally filtered by pickup/dropoff. Returns list of dicts."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    q = "SELECT * FROM runs WHERE 1=1"
    params = []
    if pickup_date:
        q += " AND pickup_date = ?"
        params.append(pickup_date)
    if dropoff_date:
        q += " AND dropoff_date = ?"
        params.append(dropoff_date)
    q += " ORDER BY run_at ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_price_per_day_history(pickup_date: str | None = None, dropoff_date: str | None = None) -> list[float]:
    """List of min_price_per_day for all runs (for stats)."""
    runs = get_all_runs(pickup_date, dropoff_date)
    return [r["min_price_per_day"] for r in runs if r["min_price_per_day"] is not None]
