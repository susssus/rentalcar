"""
Fetch current prices from rentalcars.com for the configured search (ALC, automatic, small).
Uses Playwright to handle JS-rendered content.
"""
import re
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

from config import load_config, build_search_url

logger = logging.getLogger(__name__)

# Common patterns for price text (€12.34 or 12,34 € or 12.34 EUR)
PRICE_RE = re.compile(r"[\d.,]+(?:\s*[€$]|\s*EUR|USD)")


def _parse_price_text(text: str) -> float | None:
    """Extract numeric price from string like '€ 45.00' or '123,45 €'. Returns None if not found."""
    if not text or not text.strip():
        return None
    # Normalize: remove currency symbols and spaces, replace comma with dot
    normalized = re.sub(r"[^\d.,]", "", text.strip()).replace(",", ".")
    # Take first number (could be "from 45.00" or "45.00 total")
    match = re.search(r"[\d.]+", normalized)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def _extract_prices_from_page(page) -> list[float]:
    """Extract all offer total prices from the search results page."""
    prices = []
    # Rentalcars.com often uses data attributes or specific classes for price.
    # Try multiple strategies.
    selectors = [
        '[data-testid*="price"]',
        '[data-testid*="total"]',
        '.price',
        '.totalPrice',
        '[class*="Price"]',
        '[class*="price"]',
        'span[class*="amount"]',
    ]
    seen = set()
    for sel in selectors:
        try:
            els = page.query_selector_all(sel)
            for el in els:
                text = (el.inner_text() or "").strip()
                p = _parse_price_text(text)
                if p is not None and p > 0 and p < 100_000 and p not in seen:
                    seen.add(p)
                    prices.append(p)
        except Exception as e:
            logger.debug("Selector %s: %s", sel, e)
    # Fallback: body text with € or £ and numbers
    if not prices:
        try:
            all_text = page.inner_text("body")
            for m in re.finditer(r"[€£]\s*([\d.,]+)|([\d.,]+)\s*[€£]", all_text):
                g = m.group(1) or m.group(2)
                if g:
                    try:
                        v = float(g.replace(",", "."))
                        if 0 < v < 100_000 and v not in seen:
                            seen.add(v)
                            prices.append(v)
                    except ValueError:
                        pass
        except Exception as e:
            logger.debug("Body price fallback: %s", e)
    return sorted(prices)


def fetch_prices(headless: bool = True, timeout_ms: int = 60_000) -> dict:
    """
    Open the search URL, wait for results, extract prices.
    Returns dict with: min_price, all_prices, rental_days, pickup_date, dropoff_date, url.
    """
    cfg = load_config()
    url = build_search_url(cfg)
    pu = cfg["pickup"]
    do = cfg["dropoff"]

    from datetime import date
    pickup = date(pu["year"], pu["month"], pu["day"])
    dropoff = date(do["year"], do["month"], do["day"])
    rental_days = max(1, (dropoff - pickup).days)

    result = {
        "min_price": None,
        "all_prices": [],
        "rental_days": rental_days,
        "pickup_date": str(pickup),
        "dropoff_date": str(dropoff),
        "url": url,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            # Site can be slow or JS-heavy; wait for load then allow time for results to render
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(12000)  # allow JS to render results (site can be slow)
            prices = _extract_prices_from_page(page)
            if prices:
                result["all_prices"] = prices
                result["min_price"] = min(prices)
            else:
                logger.warning("No prices found on page. Check selectors or run with --dump-html.")
        finally:
            browser.close()

    return result


def dump_page_html(output_path: Path | None = None, timeout_ms: int = 30_000) -> str:
    """Fetch the page and save HTML for debugging selectors."""
    cfg = load_config()
    url = build_search_url(cfg)
    out = output_path or Path("rentalcars_search_results.html")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(3000)
            html = page.content()
            out.write_text(html, encoding="utf-8")
            logger.info("Saved HTML to %s", out)
        finally:
            browser.close()
    return str(out)
