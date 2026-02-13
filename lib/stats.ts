import type { Run } from "./db";

export function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const s = [...values].sort((a, b) => a - b);
  const n = s.length;
  if (n % 2 === 1) return s[Math.floor(n / 2)]!;
  return (s[n / 2 - 1]! + s[n / 2]!) / 2;
}

export function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

export function percentile(values: number[], p: number): number | null {
  if (values.length === 0 || p < 0 || p > 1) return null;
  const s = [...values].sort((a, b) => a - b);
  const k = (s.length - 1) * p;
  const f = Math.floor(k);
  const c = Math.ceil(k);
  if (f === c) return s[Math.floor(k)] ?? null;
  return (s[f]! * (c - k) + s[c]! * (k - f)) as number;
}

export function computeStats(runs: Run[]): {
  count: number;
  avgPerDay: number | null;
  medianPerDay: number | null;
  p25PerDay: number | null;
} {
  const prices = runs
    .map((r) => r.min_price_per_day)
    .filter((p): p is number => p != null && p > 0);
  return {
    count: runs.length,
    avgPerDay: average(prices),
    medianPerDay: median(prices),
    p25PerDay: percentile(prices, 0.25),
  };
}

export function isCheap(
  currentPricePerDay: number,
  runs: Run[],
  cheapPercentile: number
): { cheap: boolean; threshold: number | null } {
  const prices = runs
    .map((r) => r.min_price_per_day)
    .filter((p): p is number => p != null && p > 0);
  if (prices.length < 3) return { cheap: true, threshold: null };
  const th = percentile(prices, cheapPercentile);
  if (th == null) return { cheap: false, threshold: null };
  return { cheap: currentPricePerDay <= th, threshold: th };
}
