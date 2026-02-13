import { NextRequest, NextResponse } from "next/server";
import { appendRun } from "@/lib/db";
import type { Run } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  const authHeader = request.headers.get("authorization");
  const secret = process.env.CRON_SECRET || process.env.INGEST_SECRET;
  if (secret && authHeader !== `Bearer ${secret}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const b = body as Record<string, unknown>;
  const run_at = typeof b.run_at === "string" ? b.run_at : new Date().toISOString();
  const pickup_date = typeof b.pickup_date === "string" ? b.pickup_date : "";
  const dropoff_date = typeof b.dropoff_date === "string" ? b.dropoff_date : "";
  const rental_days = typeof b.rental_days === "number" ? b.rental_days : 0;
  const min_total_price =
    typeof b.min_total_price === "number" ? b.min_total_price : null;
  const min_price_per_day =
    typeof b.min_price_per_day === "number" ? b.min_price_per_day : null;
  const num_offers = typeof b.num_offers === "number" ? b.num_offers : 0;
  const url = typeof b.url === "string" ? b.url : null;

  if (!pickup_date || !dropoff_date) {
    return NextResponse.json(
      { error: "Missing pickup_date or dropoff_date" },
      { status: 400 }
    );
  }

  const run: Run = {
    run_at,
    pickup_date,
    dropoff_date,
    rental_days,
    min_total_price,
    min_price_per_day,
    num_offers,
    url,
  };

  try {
    await appendRun(run);
    return NextResponse.json({ ok: true });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to store run";
    console.error("Ingest error:", e);
    return NextResponse.json(
      { error: "Failed to store run", detail: message },
      { status: 500 }
    );
  }
}
