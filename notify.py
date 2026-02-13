"""
Notify when prices are cheap: console + optional desktop notification (macOS).
"""
import logging
import subprocess
import sys
from config import load_config

logger = logging.getLogger(__name__)


def desktop_notify(title: str, body: str) -> bool:
    """Try to show a desktop notification. Returns True if sent."""
    try:
        cfg = load_config()
        if not cfg.get("desktop_notify", True):
            return False
    except Exception:
        pass
    # macOS
    try:
        subprocess.run(
            [
                "osascript", "-e",
                f'display notification "{body}" with title "{title}"',
            ],
            check=False,
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # Linux (notify-send)
    try:
        subprocess.run(
            ["notify-send", title, body],
            check=False,
            capture_output=True,
            timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def notify_cheap(price_per_day: float, total: float, rental_days: int, threshold: float | None, url: str) -> None:
    """Print and optionally desktop-notify that current price is cheap."""
    msg = (
        f"Rentalcars ALC: cheap rate €{price_per_day:.2f}/day (total €{total:.2f} for {rental_days} days)."
    )
    if threshold is not None:
        msg += f" Below 25th percentile (€{threshold:.2f}/day)."
    print(msg, file=sys.stderr)
    print(f"Search: {url}", file=sys.stderr)
    desktop_notify("Rentalcars ALC – cheap rate", msg)
