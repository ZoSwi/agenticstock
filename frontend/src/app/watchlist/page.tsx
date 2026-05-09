"use client";

import Link from "next/link";
import * as React from "react";

import { Shell } from "@/components/Shell";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { addToWatchlist, getWatchlist } from "@/lib/api";

export default function WatchlistPage() {
  const userId = "demo";
  const [tickers, setTickers] = React.useState<string[]>([]);
  const [ticker, setTicker] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const w = await getWatchlist(userId);
      setTickers(w.tickers || []);
    } catch (e: any) {
      setError(e?.message || "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <Shell>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Watchlist</h2>
          <p className="mt-1 text-sm text-black/60 dark:text-white/60">Save tickers for quick tracking.</p>
        </div>
        <Button variant="secondary" onClick={refresh} disabled={loading}>
          Refresh
        </Button>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Card>
          <div className="text-sm font-medium">Add a ticker</div>
          <div className="mt-3 flex gap-2">
            <Input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="e.g., NVDA" />
            <Button
              onClick={async () => {
                const t = ticker.toUpperCase().trim();
                if (!t) return;
                setLoading(true);
                try {
                  await addToWatchlist(userId, t);
                  setTicker("");
                  await refresh();
                } catch (e: any) {
                  setError(e?.message || "Failed to add");
                } finally {
                  setLoading(false);
                }
              }}
              disabled={loading || !ticker.trim()}
            >
              Add
            </Button>
          </div>
          {error ? <div className="mt-3 text-sm text-rose-600">{error}</div> : null}
        </Card>

        <Card>
          <div className="text-sm font-medium">Saved</div>
          <div className="mt-3 space-y-2">
            {tickers.length ? (
              tickers.map((t) => (
                <Link
                  key={t}
                  href={`/stocks/${t}`}
                  className="flex items-center justify-between rounded-2xl border border-black/10 bg-white/60 px-4 py-3 text-sm hover:bg-white dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
                >
                  <div className="font-medium">{t}</div>
                  <div className="text-black/60 dark:text-white/60">Open</div>
                </Link>
              ))
            ) : (
              <div className="text-sm text-black/60 dark:text-white/60">No tickers yet.</div>
            )}
          </div>
        </Card>
      </div>
    </Shell>
  );
}

