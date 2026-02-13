import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Scraping is done by the daily GitHub Action (no Chromium on Vercel).
 * This cron endpoint is a no-op; kept so existing cron config doesn’t 404.
 */
export async function GET(request: NextRequest) {
  const authHeader = request.headers.get("authorization");
  const cronSecret = process.env.CRON_SECRET;
  if (cronSecret && authHeader !== `Bearer ${cronSecret}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  return NextResponse.json({
    ok: true,
    message: "Price checks run via the daily GitHub Action; no scrape on Vercel.",
  });
}
