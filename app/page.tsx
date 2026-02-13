"use client";

import { useEffect, useState } from "react";

type Stats = {
  count: number;
  avgPerDay: number | null;
  medianPerDay: number | null;
  p25PerDay: number | null;
};

type Run = {
  run_at: string;
  min_total_price: number | null;
  min_price_per_day: number | null;
  num_offers: number;
};

type ApiStats = {
  pickup: string;
  dropoff: string;
  searchUrl: string;
  location: string;
  stats: Stats;
  lastRun: Run | null;
  recentRuns: Run[];
};

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function formatMoney(n: number) {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
  }).format(n);
}

export default function Home() {
  const [data, setData] = useState<ApiStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [runLoading, setRunLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      setError(null);
      const res = await fetch("/api/stats");
      if (!res.ok) throw new Error("Failed to load stats");
      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const runCheck = async () => {
    setRunLoading(true);
    setError(null);
    setInfo(null);
    try {
      const res = await fetch("/api/run", { method: "POST" });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? "Run failed");
      await fetchStats();
      if (json.ok === false && json.message) setInfo(json.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
    } finally {
      setRunLoading(false);
    }
  };

  if (loading) {
    return (
      <main className="main">
        <div className="loading">Loading…</div>
      </main>
    );
  }

  const last = data?.lastRun;
  const stats = data?.stats;
  const hasEnoughData = stats && stats.count >= 3 && stats.p25PerDay != null;
  const isCheap =
    hasEnoughData &&
    last?.min_price_per_day != null &&
    last.min_price_per_day <= (stats.p25PerDay ?? Infinity);

  return (
    <main className="main">
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700&display=swap"
        rel="stylesheet"
      />

      <header className="header">
        <h1>ALC car rental watcher</h1>
        <p className="subtitle">
          Alicante airport · automatic · small cars · fetch & return
        </p>
        <p className="dates">
          {data?.pickup} → {data?.dropoff}
        </p>
      </header>

      {error && (
        <div className="banner error">
          {error}
        </div>
      )}

      {info && (
        <div className="banner info">
          {info}
        </div>
      )}

      {isCheap && last && (
        <div className="banner cheap">
          Right now it’s <strong>cheap</strong> — €{last.min_price_per_day!.toFixed(2)}/day is below the 25th percentile. Good time to book.
        </div>
      )}

      <section className="cards">
        <div className="card">
          <h2>Current min</h2>
          {last ? (
            <>
              <div className="big">
                {last.min_price_per_day != null
                  ? formatMoney(last.min_price_per_day)
                  : "—"}
                <span className="unit">/day</span>
              </div>
              {last.min_total_price != null && (
                <p className="muted">
                  {formatMoney(last.min_total_price)} total · {last.num_offers} offers
                </p>
              )}
              <p className="muted small">Last run: {formatDate(last.run_at)}</p>
            </>
          ) : (
            <p className="muted">No data yet. Run a check below.</p>
          )}
        </div>

        <div className="card">
          <h2>Stats (all runs)</h2>
          {stats && stats.count > 0 ? (
            <>
              <div className="stat-row">
                <span>Average/day</span>
                <span>{stats.avgPerDay != null ? formatMoney(stats.avgPerDay) : "—"}</span>
              </div>
              <div className="stat-row">
                <span>Median/day</span>
                <span>{stats.medianPerDay != null ? formatMoney(stats.medianPerDay) : "—"}</span>
              </div>
              <div className="stat-row">
                <span>25th percentile (cheap threshold)</span>
                <span>{stats.p25PerDay != null ? formatMoney(stats.p25PerDay) : "—"}</span>
              </div>
              <p className="muted small">{stats.count} runs recorded</p>
            </>
          ) : (
            <p className="muted">Run a few checks to see averages.</p>
          )}
        </div>
      </section>

      <section className="actions">
        <button
          type="button"
          className="btn"
          onClick={runCheck}
          disabled={runLoading}
        >
          {runLoading ? "Checking…" : "Run price check now"}
        </button>
        <p className="muted small">
          Cron runs once per day. You can also trigger a check here.
        </p>
      </section>

      {data?.searchUrl && (
        <p className="search-link">
          <a href={data.searchUrl} target="_blank" rel="noopener noreferrer">
            Open search on Rentalcars.com →
          </a>
        </p>
      )}

      {data?.recentRuns && data.recentRuns.length > 0 && (
        <section className="history">
          <h2>Recent runs</h2>
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>€/day</th>
                <th>Total</th>
                <th>Offers</th>
              </tr>
            </thead>
            <tbody>
              {data.recentRuns.map((r, i) => (
                <tr key={i}>
                  <td>{formatDate(r.run_at)}</td>
                  <td>
                    {r.min_price_per_day != null
                      ? formatMoney(r.min_price_per_day)
                      : "—"}
                  </td>
                  <td>
                    {r.min_total_price != null
                      ? formatMoney(r.min_total_price)
                      : "—"}
                  </td>
                  <td>{r.num_offers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
