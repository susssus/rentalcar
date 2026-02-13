# Rentalcars ALC price watcher

Web app that polls [Rentalcars.com](https://www.rentalcars.com) for **Alicante–Elche (ALC)** airport, **fetch & return at same location**, filtered for **automatic transmission** and **small cars**. It stores price history, shows **average** and **median** price per day, and highlights when the current rate is **cheap** (below the 25th percentile).

Deploy as a **Vercel webapp** with a dashboard. Price scraping runs in a **daily GitHub Action** (so no Chromium on Vercel, avoiding the `libnss3`/serverless issues).

---

## Deploy to Vercel

1. **Push this repo to GitHub** (or connect another Git provider in Vercel).

2. **Create a Vercel project** from the repo. Vercel will detect Next.js.

3. **Add Redis**  
   In the Vercel dashboard: Project → Integrations / Storage → add a **Redis** database and connect it to your project. This stores the price history. The integration will add **REDIS_URL** (a `redis://...` connection string). Ensure it’s set for Production (and Preview if needed).

4. **Environment variables** (optional; defaults work for ALC, 25 Feb–12 Mar 2026):
   - `CRON_SECRET` or `INGEST_SECRET` – Secret used to authorize the GitHub Action when it POSTs scraped data to `/api/ingest`. Set the same value as the GitHub secret `INGEST_SECRET` (see below).
   - To change dates or filters, set the same in `config.yaml` for the Python scraper (used by the Action); the dashboard reads from Redis.
     - `PICKUP_DAY`, `PICKUP_MONTH`, `PICKUP_YEAR`, etc. in Vercel only affect the dashboard’s config display; the Action uses `config.yaml`.

5. **Deploy**  
   Deploy from the Vercel dashboard or `vercel` CLI. The app serves the **dashboard** at `/` (current min price, stats, recent runs). The “Run price check now” button explains that scraping is done by the daily GitHub Action.

---

## Daily scrape via GitHub Action

Scraping runs **on GitHub’s runners** (full Linux + Playwright), then POSTs results to your app so Vercel never runs Chromium.

1. **Secrets** (repo → Settings → Secrets and variables → Actions):
   - `INGEST_URL` – Your app’s origin, e.g. `https://your-app.vercel.app` (no trailing slash).
   - `INGEST_SECRET` – A secret string; set the same value as `CRON_SECRET` or `INGEST_SECRET` in Vercel so `/api/ingest` accepts the request.

2. **Schedule**  
   The workflow `.github/workflows/daily-scrape.yml` runs at **12:00 UTC** every day. You can also run it manually: Actions → “Daily price scrape” → “Run workflow”.

3. **Flow**  
   The Action installs Python + Playwright, runs the same scraper as the Python CLI, and POSTs the run JSON to `https://<INGEST_URL>/api/ingest`. The dashboard then shows the new data.

4. **0 offers in CI**  
   Runs from GitHub Actions often get **0 offers** because the site (Rentalcars.com) may show an error page or block automated traffic in that environment (e.g. AWS WAF, datacenter IP). A **successful** scrape (with at least one offer and price data) is more likely when you run the scraper **locally** or from a non-blocked IP. When the Action gets 0 offers, it still POSTs the run (so the dashboard records the attempt) and uploads a **debug artifact** `scrape-zero-offers-html` with the page HTML so you can inspect what the page looked like in CI (Actions → run → Artifacts).

---

## Local development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). You need **REDIS_URL** for storage: add a Redis integration to your Vercel project, then run `vercel link` and `vercel env pull .env.local` to get `REDIS_URL` locally.

The “Run price check now” button no longer runs a scrape on Vercel; it shows a short message. Data is updated by the daily GitHub Action. To test the scraper locally, use the Python CLI below and (optionally) POST the output to your app’s `/api/ingest` with the same secret.

---

## How “cheap” is decided

- Each run stores the **minimum total price** and **minimum price per day** for your date range and filters.
- **Average** and **median** price per day are computed over all stored runs.
- **Cheap** = current min price per day is at or below the **25th percentile** of historical min-per-day values (configurable via `CHEAP_PERCENTILE`). The dashboard shows a green banner when the latest run is cheap.

---

## Optional: Python CLI (local only)

The repo still includes a **Python + Playwright** script for running the same logic locally (e.g. if you prefer not to rely on the Vercel scraper or want desktop notifications):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

- **Run once:** `python main.py --once`  
- **Watch (poll every N min):** `python main.py --watch`  
- **Stats only:** `python main.py --stats`

Config: `config.yaml` (dates, `cheap_percentile`, etc.). Data is stored in `data/prices.db` (SQLite), separate from the Redis used by the webapp.
