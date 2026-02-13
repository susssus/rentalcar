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
            n_before = len(prices)
            for el in els:
                text = (el.inner_text() or "").strip()
                p = _parse_price_text(text)
                if p is not None and p > 0 and p < 100_000 and p not in seen:
                    seen.add(p)
                    prices.append(p)
            if len(prices) > n_before:
                logger.info("Selector %s: found %d price(s) (total %d)", sel, len(prices) - n_before, len(prices))
        except Exception as e:
            logger.debug("Selector %s: %s", sel, e)
    # Fallback 1: run regex in browser (same DOM as user; handles "237 €" from e.g. Finnish page)
    if not prices:
        logger.info("No prices from CSS selectors; trying browser regex on body text.")
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
                if prices:
                    logger.info("Browser regex fallback: found %d price(s)", len(prices))
        except Exception as e:
            logger.debug("Browser price fallback: %s", e)

    # Fallback 2: body text with € or £ and numbers (server-side)
    if not prices:
        logger.info("Trying server-side regex on body text.")
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
                if prices:
                    logger.info("Body text fallback: found %d price(s)", len(prices))
        except Exception as e:
            logger.debug("Body price fallback: %s", e)
    logger.info("Extraction complete: %d total price(s) found", len(prices))
    return sorted(prices)


def _accept_cookie_consent(page, wait_banner_ms: int = 4000, click_timeout_ms: int = 2000) -> None:
    """Find OneTrust Accept button (footer banner), scroll into view, click. Kept short for CI timeout."""
    try:
        btn = None
        try:
            btn = page.wait_for_selector(
                "#onetrust-accept-btn-handler",
                state="attached",
                timeout=wait_banner_ms,
            )
        except Exception:
            pass
        if not btn:
            try:
                btn = page.get_by_role("button", name=re.compile(r"Hyväksyn|Accept", re.I)).first
                btn.wait_for(state="attached", timeout=2000)
            except Exception:
                pass
        if btn:
            btn.scroll_into_view_if_needed(timeout=click_timeout_ms)
            page.wait_for_timeout(200)
            btn.click(timeout=click_timeout_ms)
            page.wait_for_timeout(1000)
            logger.info("Cookie consent: clicked Accept (Hyväksyn).")
        else:
            logger.info("Cookie consent: no banner found, skipping.")
    except Exception as e:
        logger.info("Cookie consent: %s", e)


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


def _click_search_button(page, timeout_ms: int = 6000) -> None:
    """Click the 'Hae' (Search) submit button so the search actually runs. Kept short for CI."""
    try:
        btn = page.get_by_role("button", name=re.compile(r"Hae|Search", re.I)).first
        btn.wait_for(state="visible", timeout=timeout_ms)
        btn.scroll_into_view_if_needed(timeout=2000)
        page.wait_for_timeout(200)
        btn.click(timeout=2000)
        logger.info("Clicked Search (Hae) to trigger results.")
    except Exception as e:
        logger.info("Search button click skipped or failed — %s", e)


def _wait_for_results(page, extra_wait_ms: int = 12_000) -> None:
    """Accept cookie banner, click Search (Hae), then wait for price content. Timings kept under 2min CI."""
    logger.info("Looking for cookie banner (Accept), then triggering search...")
    page.wait_for_timeout(1000)
    _accept_cookie_consent(page)
    page.wait_for_timeout(500)
    _click_search_button(page)
    remaining = max(0, extra_wait_ms - 2000)
    logger.info("Waiting %.1fs for results to load...", remaining / 1000.0)
    page.wait_for_timeout(remaining)
    logger.info("Waiting up to 18s for body to contain a price (€ + digits)...")
    try:
        page.wait_for_function(
            "document.body && document.body.innerText && document.body.innerText.match(/[€£]\\s*[\\d,.]+|[\\d,.]+\\s*[€£]/)",
            timeout=18_000,
        )
        logger.info("Price-like text detected in body.")
    except Exception:
        logger.info("No price-like text in body within timeout; continuing to extract anyway.")
    page.wait_for_timeout(1500)


def fetch_prices(headless: bool = True, timeout_ms: int = 45_000) -> dict:
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

    logger.info("Scrape start: url=%s, headless=%s, timeout=%dms", url, headless, timeout_ms)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            logger.info("Navigating to search URL...")
            page.goto(url, wait_until="load", timeout=timeout_ms)
            logger.info("Page load complete. Waiting for results (WAF + cookie + price content)...")
            _wait_for_results(page, extra_wait_ms=12_000)
            if _page_has_error_message(page):
                logger.warning("Page shows error message (e.g. Jokin meni pieleen). Retrying once after reload...")
                page.reload(wait_until="load", timeout=timeout_ms)
                _wait_for_results(page, extra_wait_ms=15_000)
            if _page_has_error_message(page):
                logger.warning("Page still shows error after retry. Site may be blocking automation.")
            logger.info("Extracting prices from page...")
            prices = _extract_prices_from_page(page)
            if prices:
                result["all_prices"] = prices
                result["min_price"] = min(prices)
                logger.info("Scrape success: min_total=%.2f €, num_offers=%d", result["min_price"], len(prices))
            else:
                logger.warning("Scrape finished with 0 offers. Check selectors or run with --dump-html.")
        finally:
            browser.close()

    return result


def dump_page_html(output_path: Path | None = None, timeout_ms: int = 90_000) -> str:
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
            _wait_for_results(page, extra_wait_ms=25_000)
            if _page_has_error_message(page):
                page.reload(wait_until="load", timeout=timeout_ms)
                _wait_for_results(page, extra_wait_ms=30_000)
            html = page.content()
            out.write_text(html, encoding="utf-8")
            logger.info("Saved HTML to %s", out)
        finally:
            browser.close()
    return str(out)
