"use client";

import { useSearchParams } from "next/navigation";
import * as React from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { fetchAnalysis, type StockAnalysis } from "@/lib/api";

type CompareItemState = {
  status: "loading" | "ready" | "error";
  data?: StockAnalysis;
  error?: string;
};

function toneOutlook(outlook: StockAnalysis["outlook"]) {
  if (outlook === "bullish") return "bullish";
  if (outlook === "bearish") return "bearish";
  return "neutral";
}

function normalizeTicker(raw: string) {
  return raw.toUpperCase().trim();
}

function isLikelyTicker(value: string) {
  return /^[A-Z.\-]{1,10}$/.test(value);
}

export function CompareClient() {
  const sp = useSearchParams();
  const seed = sp.get("t") || "";

  const [tickers, setTickers] = React.useState<string[]>(seed ? [seed] : ["AAPL", "MSFT"]);
  const [input, setInput] = React.useState("");
  const [items, setItems] = React.useState<Record<string, CompareItemState>>({});
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const unique = Array.from(new Set(tickers.map((t) => normalizeTicker(t)).filter(Boolean))).slice(0, 4);
    setTickers(unique);
    setItems((prev) => {
      const next = { ...prev };
      for (const ticker of unique) next[ticker] = { status: "loading" };
      return next;
    });

    const results = await Promise.allSettled(unique.map(async (ticker) => [ticker, await fetchAnalysis(ticker)] as const));
    const next: Record<string, CompareItemState> = {};
    for (let i = 0; i < unique.length; i += 1) {
      const ticker = unique[i];
      const result = results[i];
      if (result.status === "fulfilled") {
        next[ticker] = { status: "ready", data: result.value[1] };
      } else {
        next[ticker] = {
          status: "error",
          error: String((result.reason as any)?.message || "Ticker unavailable"),
        };
      }
    }
    setItems(next);
    setLoading(false);
  }, [tickers]);

  React.useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Compare</h2>
          <p className="mt-1 text-sm text-black/60 dark:text-white/60">
            Side-by-side directional outlooks (no exact price predictions).
          </p>
        </div>
        <div className="flex w-full gap-2 md:w-auto">
          <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Add ticker (e.g., NVDA)" />
          <Button
            variant="secondary"
            onClick={() => {
              const ticker = normalizeTicker(input);
              if (!ticker) return;
              if (!isLikelyTicker(ticker)) {
                setError("Invalid ticker format. Use symbols like AAPL, BRK-B, BTC-USD.");
                return;
              }
              setTickers((prev) => [...prev, ticker]);
              setInput("");
              setError(null);
            }}
          >
            Add
          </Button>
          <Button onClick={load} disabled={loading}>
            Refresh
          </Button>
        </div>
      </div>

      {error ? <div className="mt-4 text-sm text-rose-600">{error}</div> : null}

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {tickers.map((ticker) => {
          const item = items[ticker];
          const analysis = item?.data;
          return (
            <Card key={ticker}>
              <div className="flex items-center justify-between">
                <div className="text-lg font-semibold">{ticker}</div>
                {item?.status === "ready" && analysis ? (
                  <Badge tone={toneOutlook(analysis.outlook) as any}>{analysis.outlook}</Badge>
                ) : item?.status === "error" ? (
                  <Badge tone="riskHigh">error</Badge>
                ) : (
                  <Badge>loading</Badge>
                )}
              </div>
              {item?.status === "ready" && analysis ? (
                <div className="mt-4 grid gap-2 text-sm text-black/70 dark:text-white/70">
                  {analysis.model_status?.degraded ? (
                    <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-800 dark:text-amber-200">
                      Model degraded: {analysis.model_status.reason || "using conservative fallback"}
                    </div>
                  ) : null}
                  <div className="flex items-center justify-between">
                    <span>Up probability</span>
                    <span className="font-medium">{Math.round(analysis.rise_probability * 100)}%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Down risk</span>
                    <span className="font-medium">{Math.round(analysis.fall_probability * 100)}%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Confidence</span>
                    <span className="font-medium">{Math.round(analysis.confidence_score * 100)}%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Suggested action</span>
                    <span className="font-medium">{analysis.suggested_action}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Model source</span>
                    <span className="font-medium">{analysis.model_status?.source || "unknown"}</span>
                  </div>
                </div>
              ) : item?.status === "error" ? (
                <div className="mt-4 text-sm text-rose-600">Ticker unavailable or provider failed.</div>
              ) : (
                <div className="mt-4 text-sm text-black/60 dark:text-white/60">Fetching...</div>
              )}
            </Card>
          );
        })}
      </div>
    </>
  );
}

