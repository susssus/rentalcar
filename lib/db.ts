import { Redis } from "@upstash/redis";

const RUNS_KEY = "rentalcars:runs";
const MAX_RUNS = 500;

function getRedis() {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) {
    throw new Error("Missing UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN");
  }
  return new Redis({ url, token });
}

export type Run = {
  run_at: string;
  pickup_date: string;
  dropoff_date: string;
  rental_days: number;
  min_total_price: number | null;
  min_price_per_day: number | null;
  num_offers: number;
  url: string | null;
};

export async function appendRun(run: Run): Promise<void> {
  const redis = getRedis();
  const runs = await getRuns();
  runs.push(run);
  const trimmed = runs.slice(-MAX_RUNS);
  await redis.set(RUNS_KEY, JSON.stringify(trimmed));
}

export async function getRuns(): Promise<Run[]> {
  try {
    const redis = getRedis();
    const raw = await redis.get<string>(RUNS_KEY);
    if (raw == null) return [];
    const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function getRunsForDates(
  pickupDate: string,
  dropoffDate: string
): Promise<Run[]> {
  const runs = await getRuns();
  return runs.filter(
    (r) => r.pickup_date === pickupDate && r.dropoff_date === dropoffDate
  );
}
