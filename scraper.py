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

# Common patterns for price text (€12.34 or 12,34 € or 12.34 EUR). &nbsp; becomes space in innerText.
PRICE_RE = re.compile(r"[\d.,]+(?:\s*[€$]|\s*EUR|USD)")
# Match "237 €" or "€ 237" or "237 EUR" from body text (used in browser evaluate)
PRICE_JS_RE = r"(\d{2,5}(?:[.,]\d{2})?)\s*[€£]|[€£]\s*(\d{2,5}(?:[.,]\d{2})?)|\d{2,5}(?:[.,]\d{2})?\s*EUR"


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
        # Rentalcars Finnish/CCJ DOM: total price in div with hashed class e.g. "237 €"
        '[class*="SM_3e7a1efe"]',
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
    # Fallback 1: run regex in browser (same DOM as user; handles "237 €" from e.g. Finnish page)
    if not prices:
        try:
            browser_prices = page.evaluate("""
                () => {
                    const body = document.body;
                    if (!body) return [];
                    const text = (body.innerText || '').replace(/\\s+/g, ' ');
                    const re = /(\\d{2,5}(?:[.,]\\d{2})?)\\s*[€£]|[€£]\\s*(\\d{2,5}(?:[.,]\\d{2})?)|(\\d{2,5}(?:[.,]\\d{2})?)\\s*EUR/gi;
                    const out = [];
                    let m;
                    while ((m = re.exec(text)) !== null) {
                        const raw = (m[1] || m[2] || m[3] || '').replace(',', '.');
                        const num = parseFloat(raw, 10);
                        if (!isNaN(num) && num > 10 && num < 100000) out.push(num);
                    }
                    return [...new Set(out)];
                }
            """)
            if isinstance(browser_prices, list):
                for n in browser_prices:
                    if isinstance(n, (int, float)) and 10 < n < 100_000 and n not in seen:
                        seen.add(n)
                        prices.append(round(float(n), 2))
        except Exception as e:
            logger.debug("Browser price fallback: %s", e)

    # Fallback 2: body text with € or £ and numbers (server-side)
    if not prices:
        try:
            all_text = page.inner_text("body") or ""
            for m in re.finditer(r"[€£]\s*([\d.,]+)|([\d.,]+)\s*[€£]|(\d{2,5}(?:[.,]\d{2})?)\s*EUR", all_text, re.IGNORECASE):
                g = m.group(1) or m.group(2) or m.group(3)
                if g:
                    try:
                        v = float(g.replace(",", "."))
                        if 10 < v < 100_000 and v not in seen:
                            seen.add(v)
                            prices.append(v)
                    except ValueError:
                        pass
        except Exception as e:
            logger.debug("Body price fallback: %s", e)
    return sorted(prices)


def _accept_cookie_consent(page, timeout_ms: int = 5000) -> None:
    """Click OneTrust 'Accept' (Hyväksyn) if the banner is visible."""
    try:
        btn = page.query_selector("#onetrust-accept-btn-handler")
        if btn:
            btn.click(timeout=timeout_ms)
            page.wait_for_timeout(1500)  # let banner dismiss
    except Exception as e:
        logger.debug("Cookie consent click skipped or failed: %s", e)


def _page_has_error_message(page) -> bool:
    """True if the page shows the Finnish error state (e.g. 'Jokin meni pieleen')."""
    try:
        el = page.query_selector('[data-testid="error-message"]')
        if el and el.is_visible():
            return True
        text = (page.inner_text("body") or "").lower()
        return "jokin meni pieleen" in text or "päivitä sivu" in text
    except Exception:
        return False


def _wait_for_results(page, extra_wait_ms: int = 18_000) -> None:
    """Wait for WAF/cookies then for price-like content. Accept cookie banner first."""
    page.wait_for_timeout(3000)  # let WAF script start
    _accept_cookie_consent(page)
    page.wait_for_timeout(max(0, extra_wait_ms - 3000 - 2000))  # rest of initial wait (minus cookie click buffer)
    try:
        page.wait_for_function(
            "document.body && document.body.innerText && document.body.innerText.match(/[€£]\\s*[\\d,.]+|[\\d,.]+\\s*[€£]/)",
            timeout=20_000,
        )
    except Exception:
        pass
    page.wait_for_timeout(3000)


def fetch_prices(headless: bool = True, timeout_ms: int = 35_000) -> dict:
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
            page.goto(url, wait_until="load", timeout=timeout_ms)
            _wait_for_results(page, extra_wait_ms=18_000)
            if _page_has_error_message(page):
                logger.warning("Page showed error message; retrying once after reload.")
                page.reload(wait_until="load", timeout=timeout_ms)
                _wait_for_results(page, extra_wait_ms=20_000)
            prices = _extract_prices_from_page(page)
            if prices:
                result["all_prices"] = prices
                result["min_price"] = min(prices)
            else:
                if _page_has_error_message(page):
                    logger.warning("Page still shows error (e.g. Jokin meni pieleen). Site may block automation.")
                logger.warning("No prices found on page. Check selectors or run with --dump-html.")
        finally:
            browser.close()

    return result


def dump_page_html(output_path: Path | None = None, timeout_ms: int = 60_000) -> str:
    """Fetch the page and save HTML for debugging selectors."""
    cfg = load_config()
    url = build_search_url(cfg)
    out = output_path or Path("rentalcars_search_results.html")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.goto(url, wait_until="load", timeout=timeout_ms)
            _wait_for_results(page, extra_wait_ms=18_000)
            if _page_has_error_message(page):
                page.reload(wait_until="load", timeout=timeout_ms)
                _wait_for_results(page, extra_wait_ms=20_000)
            html = page.content()
            out.write_text(html, encoding="utf-8")
            logger.info("Saved HTML to %s", out)
        finally:
            browser.close()
    return str(out)
