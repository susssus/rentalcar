import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Scraping runs on GitHub Actions (daily) and POSTs to /api/ingest.
 * This endpoint no longer runs Puppeteer on Vercel (avoids libnss3/serverless issues).
 */
export async function POST() {
  return NextResponse.json({
    ok: false,
    message:
      "Price checks run via the daily GitHub Action and POST to the app. Use the dashboard to view the latest data, or trigger the workflow manually in the repo’s Actions tab.",
  });
}
