import { NextRequest, NextResponse } from "next/server";
import { fetchPrices } from "@/lib/scraper";
import { appendRun } from "@/lib/db";
import { getRunsForDates } from "@/lib/db";
import { computeStats, isCheap } from "@/lib/stats";
import {
  getPickupDateStr,
  getDropoffDateStr,
  searchConfig,
} from "@/lib/config";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(request: NextRequest) {
  const authHeader = request.headers.get("authorization");
  const cronSecret = process.env.CRON_SECRET;
  if (cronSecret && authHeader !== `Bearer ${cronSecret}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const data = await fetchPrices(55_000);

    const min_total = data.min_price ?? null;
    const rental_days = data.rental_days;
    const min_per_day =
      min_total != null && rental_days > 0 ? min_total / rental_days : null;

    await appendRun({
      run_at: new Date().toISOString(),
      pickup_date: data.pickup_date,
      dropoff_date: data.dropoff_date,
      rental_days: data.rental_days,
      min_total_price: min_total,
      min_price_per_day: min_per_day,
      num_offers: data.all_prices.length,
      url: data.url,
    });

    const pickup = getPickupDateStr();
    const dropoff = getDropoffDateStr();
    const runs = await getRunsForDates(pickup, dropoff);
    const { cheap, threshold } =
      min_per_day != null
        ? isCheap(min_per_day, runs, searchConfig.cheapPercentile)
        : { cheap: false, threshold: null };

    return NextResponse.json({
      ok: true,
      min_total_price: min_total,
      min_price_per_day: min_per_day,
      num_offers: data.all_prices.length,
      cheap,
      cheap_threshold: threshold,
      url: data.url,
    });
  } catch (e) {
    console.error("Cron check-prices error:", e);
    return NextResponse.json(
      { error: String(e instanceof Error ? e.message : "Scrape failed") },
      { status: 500 }
    );
  }
}
