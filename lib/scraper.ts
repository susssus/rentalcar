import puppeteer, { type Page } from "puppeteer-core";
import chromium from "@sparticuz/chromium";
import {
  buildSearchUrl,
  getRentalDays,
  getPickupDateStr,
  getDropoffDateStr,
} from "./config";

// Reduces serverless footprint; required for Vercel (avoids extra lib deps)
chromium.setGraphicsMode = false;

export type ScrapeResult = {
  min_price: number | null;
  all_prices: number[];
  rental_days: number;
  pickup_date: string;
  dropoff_date: string;
  url: string;
};

function parsePriceText(text: string): number | null {
  if (!text?.trim()) return null;
  const normalized = text.replace(/[^\d.,]/g, "").replace(",", ".");
  const match = normalized.match(/[\d.]+/);
  if (match) {
    const v = parseFloat(match[0]!);
    return Number.isFinite(v) && v > 0 && v < 100_000 ? v : null;
  }
  return null;
}

async function extractPricesFromPage(page: Page): Promise<number[]> {
  const prices: number[] = [];
  const seen = new Set<number>();

  const selectors = [
    '[data-testid*="price"]',
    '[data-testid*="total"]',
    ".price",
    ".totalPrice",
    '[class*="Price"]',
    '[class*="price"]',
    'span[class*="amount"]',
  ];

  for (const sel of selectors) {
    try {
      const els = await page.$$(sel);
      for (const el of els) {
        const text = await el.evaluate((e) => (e as HTMLElement).innerText?.trim() ?? "");
        const p = parsePriceText(text);
        if (p != null && !seen.has(p)) {
          seen.add(p);
          prices.push(p);
        }
      }
    } catch {
      // ignore
    }
  }

  if (prices.length === 0) {
    const body = await page.evaluate(() => document.body?.innerText ?? "");
    const re = /€\s*([\d.,]+)|([\d.,]+)\s*€/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(body)) !== null) {
      const g = m[1] ?? m[2];
      if (g) {
        const v = parseFloat(g.replace(",", "."));
        if (v > 0 && v < 100_000 && !seen.has(v)) {
          seen.add(v);
          prices.push(v);
        }
      }
    }
  }

  return prices.sort((a, b) => a - b);
}

export async function fetchPrices(timeoutMs = 55_000): Promise<ScrapeResult> {
  const url = buildSearchUrl();
  const rental_days = getRentalDays();
  const pickup_date = getPickupDateStr();
  const dropoff_date = getDropoffDateStr();

  const result: ScrapeResult = {
    min_price: null,
    all_prices: [],
    rental_days,
    pickup_date,
    dropoff_date,
    url,
  };

  const browser = await puppeteer.launch({
    args: chromium.args,
    defaultViewport: { width: 1280, height: 800, deviceScaleFactor: 1 },
    executablePath: await chromium.executablePath(),
    headless: true,
  });

  try {
    const page = await browser.newPage();
    await page.setUserAgent(
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    );
    await page.goto(url, {
      waitUntil: "load",
      timeout: timeoutMs,
    });
    await new Promise((r) => setTimeout(r, 8000));

    const all_prices = await extractPricesFromPage(page);
    result.all_prices = all_prices;
    if (all_prices.length > 0) result.min_price = Math.min(...all_prices);
  } finally {
    await browser.close();
  }

  return result;
}
