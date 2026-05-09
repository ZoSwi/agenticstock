"use client";

import { useRouter } from "next/navigation";
import * as React from "react";

import { searchStocks } from "@/lib/api";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export function TickerSearch({ className }: { className?: string }) {
  const router = useRouter();
  const [q, setQ] = React.useState("");
  const [results, setResults] = React.useState<Array<{ ticker: string; name?: string | null }>>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [activeIndex, setActiveIndex] = React.useState<number>(-1);

  const typed = q.trim().toUpperCase();
  const canOpenTyped = /^[A-Z.\-]{1,10}$/.test(typed);

  const openTypedTicker = React.useCallback(() => {
    if (!typed) return;
    const exact = results.find((r) => r.ticker.toUpperCase() === typed);
    if (exact) {
      router.push(`/stocks/${encodeURIComponent(exact.ticker)}`);
      return;
    }
    if (results.length > 0) {
      router.push(`/stocks/${encodeURIComponent(results[0].ticker)}`);
      return;
    }
    // Only allow raw ticker open for short symbol-like inputs.
    if (canOpenTyped && typed.length <= 5) {
      router.push(`/stocks/${encodeURIComponent(typed)}`);
    }
  }, [canOpenTyped, results, router, typed]);

  const openResultAt = React.useCallback(
    (idx: number) => {
      if (idx < 0 || idx >= results.length) return;
      router.push(`/stocks/${encodeURIComponent(results[idx].ticker)}`);
    },
    [results, router]
  );

  React.useEffect(() => {
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      const query = q.trim();
      if (query.length < 1) {
        setResults([]);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const data = await searchStocks(query.toUpperCase(), ctrl.signal);
        setResults(data.results || []);
        setActiveIndex((data.results || []).length ? 0 : -1);
      } catch (e: any) {
        if (ctrl.signal.aborted) return;
        setError(e?.message || "Search failed");
      } finally {
        if (!ctrl.signal.aborted) setLoading(false);
      }
    }, 120);
    return () => {
      ctrl.abort();
      clearTimeout(t);
    };
  }, [q]);

  return (
    <div className={cn("w-full", className)}>
      <div className="flex items-center gap-2">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search ticker (e.g., TSLA, AAPL)"
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              if (!results.length) return;
              setActiveIndex((v) => (v + 1) % results.length);
              return;
            }
            if (e.key === "ArrowUp") {
              e.preventDefault();
              if (!results.length) return;
              setActiveIndex((v) => (v <= 0 ? results.length - 1 : v - 1));
              return;
            }
            if (e.key === "Enter") {
              e.preventDefault();
              if (activeIndex >= 0 && results[activeIndex]) {
                openResultAt(activeIndex);
                return;
              }
              openTypedTicker();
            }
          }}
        />
        <Button variant="secondary" onClick={openTypedTicker} disabled={!canOpenTyped} className="h-11">
          Open
        </Button>
      </div>
      <div className="mt-3 space-y-2">
        {loading ? <div className="text-sm text-black/60 dark:text-white/60">Searching...</div> : null}
        {error ? <div className="text-sm text-rose-600">{error}</div> : null}
        {!loading && !error && typed.length > 0 && results.length === 0 && canOpenTyped && typed.length <= 5 ? (
          <button
            type="button"
            onClick={openTypedTicker}
            className="flex w-full items-center justify-between rounded-2xl border border-black/10 bg-white/60 px-4 py-3 text-sm hover:bg-white dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
          >
            <div className="font-medium">{typed}</div>
            <div className="max-w-[70%] truncate text-right text-black/60 dark:text-white/60">Open symbol</div>
          </button>
        ) : null}
        {results.slice(0, 6).map((r, i) => (
          <button
            key={r.ticker}
            type="button"
            onMouseEnter={() => setActiveIndex(i)}
            onClick={() => openResultAt(i)}
            className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-sm dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10 ${
              i === activeIndex
                ? "border-black/25 bg-white dark:border-white/25 dark:bg-white/10"
                : "border-black/10 bg-white/60 hover:bg-white"
            }`}
          >
            <div className="font-medium">{r.ticker}</div>
            <div className="max-w-[70%] truncate text-right text-black/60 dark:text-white/60">{r.name || "-"}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
