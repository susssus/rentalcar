import { NextResponse } from "next/server";
import { getRunsForDates } from "@/lib/db";
import { computeStats } from "@/lib/stats";
import {
  getPickupDateStr,
  getDropoffDateStr,
  buildSearchUrl,
  searchConfig,
} from "@/lib/config";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    const pickup = getPickupDateStr();
    const dropoff = getDropoffDateStr();
    const runs = await getRunsForDates(pickup, dropoff);
    // Successful scrape = run with at least one offer (non-zero price info)
    const successfulRuns = runs.filter((r) => r.num_offers > 0);
    const stats = computeStats(successfulRuns);

    const lastRun =
      successfulRuns.length > 0
        ? successfulRuns[successfulRuns.length - 1]!
        : null;
    const recentRuns = runs.slice(-20).reverse();

    return NextResponse.json({
      pickup,
      dropoff,
      searchUrl: buildSearchUrl(),
      location: searchConfig.location.iata,
      stats: {
        count: stats.count,
        avgPerDay: stats.avgPerDay,
        medianPerDay: stats.medianPerDay,
        p25PerDay: stats.p25PerDay,
      },
      lastRun: lastRun
        ? {
            run_at: lastRun.run_at,
            min_total_price: lastRun.min_total_price,
            min_price_per_day: lastRun.min_price_per_day,
            num_offers: lastRun.num_offers,
          }
        : null,
      recentRuns,
    });
  } catch (e) {
    console.error("Stats API error:", e);
    return NextResponse.json(
      { error: "Failed to load stats" },
      { status: 500 }
    );
  }
}
