# Rentalcars ALC price watcher

Web app that polls [Rentalcars.com](https://www.rentalcars.com) for **Alicante–Elche (ALC)** airport, **fetch & return at same location**, filtered for **automatic transmission** and **small cars**. It stores price history, shows **average** and **median** price per day, and highlights when the current rate is **cheap** (below the 25th percentile).

Deploy as a **Vercel webapp** with a dashboard and a cron job that runs once per day.

---

## Deploy to Vercel

1. **Push this repo to GitHub** (or connect another Git provider in Vercel).

2. **Create a Vercel project** from the repo. Vercel will detect Next.js.

3. **Add Upstash Redis**  
   In the Vercel dashboard: Project → Integrations → search **Upstash** → add the Redis integration and connect a database (or create one). This stores the price history. The integration injects `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`.

4. **Environment variables** (optional; defaults work for ALC, 25 Feb–12 Mar 2026):
   - `CRON_SECRET` – Set a secret string. Vercel sends it as `Authorization: Bearer <CRON_SECRET>` when invoking the cron. Add the same value in Project → Settings → Cron → Secret so the cron endpoint can validate requests.
   - To change dates or filters, set:
     - `PICKUP_DAY`, `PICKUP_MONTH`, `PICKUP_YEAR`, `PICKUP_HOUR`, `PICKUP_MINUTE`
     - `DROPOFF_DAY`, `DROPOFF_MONTH`, `DROPOFF_YEAR`, `DROPOFF_HOUR`, `DROPOFF_MINUTE`
     - `LOCATION_IATA`, `LOCATION_NAME`, `LOCATION_COORDINATES`
     - `DRIVERS_AGE`, `FILTER_TRANSMISSION`, `FILTER_CAR_CATEGORY`
     - `CHEAP_PERCENTILE` (e.g. `0.25`)

5. **Enable Cron**  
   The repo includes `vercel.json` with a cron that hits `/api/cron/check-prices` once per day (12:00 UTC), which fits Vercel Hobby’s cron limits (see [Vercel Cron](https://vercel.com/docs/cron-jobs)).

6. **Deploy**  
   Deploy from the Vercel dashboard or `vercel` CLI. The app will:
   - Serve the **dashboard** at `/` (current min price, stats, recent runs, “Run price check now”).
   - Run the **scraper** on schedule via cron (or when you click “Run price check now”). The scraper uses Puppeteer + Chromium on Vercel’s serverless runtime (max duration 60s on Pro).

---

## Local development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). You need **Upstash Redis** for storage: add the Upstash integration to your Vercel project, then run `vercel link` and `vercel env pull .env.local` to get `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` locally.

To trigger a price check locally: click “Run price check now” in the UI, or `curl -X POST http://localhost:3000/api/run`.

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

Config: `config.yaml` (dates, `cheap_percentile`, etc.). Data is stored in `data/prices.db` (SQLite), separate from the Upstash Redis used by the webapp.
