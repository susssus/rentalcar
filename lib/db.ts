import { createClient } from "redis";

const RUNS_KEY = "rentalcars:runs";
const MAX_RUNS = 500;

type RedisClient = Awaited<ReturnType<typeof createClient>>;
let clientPromise: Promise<RedisClient> | null = null;

async function getClient(): Promise<RedisClient> {
  if (clientPromise) return clientPromise;
  const url = process.env.REDIS_URL;
  if (!url) {
    throw new Error("Missing REDIS_URL");
  }
  const client = createClient({ url });
  clientPromise = client.connect().then(() => client as RedisClient);
  return clientPromise;
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
  const client = await getClient();
  const runs = await getRuns();
  runs.push(run);
  const trimmed = runs.slice(-MAX_RUNS);
  await client.set(RUNS_KEY, JSON.stringify(trimmed));
}

export async function getRuns(): Promise<Run[]> {
  try {
    const client = await getClient();
    const raw = await client.get(RUNS_KEY);
    if (raw == null) return [];
    const parsed = JSON.parse(raw);
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
