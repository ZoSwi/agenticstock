"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { fetchPriceSeries, fetchQuoteDetail, fetchSignals, getMarketStreamUrl, type StockPriceSeries, type StockQuoteDetail } from "@/lib/api";

function fmtPrice(v: number | null | undefined): string { return v == null ? "--" : `$${v.toFixed(2)}`; }
function fmtPct(v: number | null | undefined): string { return v == null ? "--" : `${v > 0 ? "+" : ""}${v.toFixed(2)}%`; }
function tone(v: number | null | undefined): "bullish" | "bearish" | "neutral" { return v == null ? "neutral" : v > 0 ? "bullish" : v < 0 ? "bearish" : "neutral"; }

export function StockLivePanel({ ticker }: { ticker: string }) {
  const [series, setSeries] = useState<StockPriceSeries | null>(null);
  const [spySeries, setSpySeries] = useState<StockPriceSeries | null>(null);
  const [live, setLive] = useState<StockPriceSeries["live_quote"] | null>(null);
  const [quoteDetail, setQuoteDetail] = useState<StockQuoteDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdateEt, setLastUpdateEt] = useState<string | null>(null);
  const [dailyDays, setDailyDays] = useState(90);
  const [mode, setMode] = useState<"daily" | "intraday">("daily");
  const [session, setSession] = useState<"1D" | "5D">("1D");
  const [resolution, setResolution] = useState<"1" | "5">("5");
  const [compareSpy, setCompareSpy] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const query = mode === "daily" ? { mode, days: dailyDays } : { mode, session, resolution };
    Promise.all([fetchPriceSeries(ticker, query), fetchQuoteDetail(ticker)])
      .then(([data, d]) => {
        if (cancelled) return;
        setSeries(data);
        setLive(data.live_quote || null);
        setQuoteDetail(d);
        setLastUpdateEt(new Date().toLocaleTimeString("en-US", { hour12: false }));
      })
      .catch(() => !cancelled && setSeries(null))
      .finally(() => !cancelled && setLoading(false));
    if (compareSpy && ticker.toUpperCase() !== "SPY") {
      void fetchPriceSeries("SPY", query).then((d) => !cancelled && setSpySeries(d)).catch(() => !cancelled && setSpySeries(null));
    } else setSpySeries(null);
    return () => { cancelled = true; };
  }, [ticker, mode, dailyDays, session, resolution, compareSpy]);

  useEffect(() => {
    const es = new EventSource(getMarketStreamUrl(30, 12));
    const onPulse = (evt: MessageEvent) => {
      try {
        const p = JSON.parse(evt.data);
        for (const b of ["top_gainers", "top_losers", "most_active"]) {
          for (const row of p?.[b] || []) {
            if (String(row?.ticker || "").toUpperCase() === ticker.toUpperCase()) {
              setLive(row);
              setLastUpdateEt(new Date().toLocaleTimeString("en-US", { hour12: false }));
              return;
            }
          }
        }
      } catch {}
    };
    es.addEventListener("pulse", onPulse);
    return () => { es.removeEventListener("pulse", onPulse); es.close(); };
  }, [ticker]);

  useEffect(() => {
    const id = setInterval(() => {
      void fetchSignals(ticker).then((s) => s?.current_update?.quote && setLive(s.current_update.quote)).catch(() => {});
      void fetchQuoteDetail(ticker).then((d) => setQuoteDetail(d)).catch(() => {});
    }, 20000);
    return () => clearInterval(id);
  }, [ticker]);

  const points = series?.points || [];
  const shownPrice = live?.last ?? series?.stats.latest_close ?? null;
  const shownChangePct = live?.change_pct ?? series?.stats.daily_change_pct ?? null;
  const minLow = Math.min(...points.map((p) => p.low), Infinity);
  const maxHigh = Math.max(...points.map((p) => p.high), -Infinity);
  const priceRange = Math.max(0.0001, maxHigh - minLow);
  const maxVolume = Math.max(...points.map((p) => p.volume || 0), 1);
  const candleW = Math.max(0.65, Math.min(2.1, 100 / Math.max(1, points.length) * 0.82));

  const spyLine = useMemo(() => {
    const a = points; const b = spySeries?.points || [];
    if (!a.length || !b.length) return "";
    const n = Math.min(a.length, b.length);
    const a0 = a[a.length - n].close || 1;
    const b0 = b[b.length - n].close || 1;
    return Array.from({ length: n }, (_, i) => {
      const x = (i / Math.max(1, n - 1)) * 100;
      const av = ((a[a.length - n + i].close / a0) - 1) * 100;
      const bv = ((b[b.length - n + i].close / b0) - 1) * 100;
      const delta = bv - av;
      const y = 50 - Math.max(-8, Math.min(8, delta));
      return `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    }).join(" ");
  }, [points, spySeries?.points]);

  const tradeSignal = shownChangePct == null ? "Hold" : shownChangePct >= 1 ? "Momentum Long" : shownChangePct <= -1 ? "Risk-Off" : "Wait";
  const stopPct = mode === "intraday" ? 0.8 : 2.0;
  const entry = shownPrice ?? 0;
  const stop = entry ? entry * (1 - stopPct / 100) : 0;
  const target = entry ? entry * (1 + (stopPct * 1.8) / 100) : 0;

  return (
    <div className="grid gap-4 xl:grid-cols-[1.5fr_0.9fr]">
      <Card className="border-black/12 bg-white/80 p-4 dark:border-white/12 dark:bg-black/20">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="text-base font-semibold">{ticker}</div>
            <Badge tone={tone(shownChangePct)}>{fmtPct(shownChangePct)}</Badge>
          </div>
          <div className="text-right">
            <div className="text-xl font-semibold tabular-nums md:text-2xl">{fmtPrice(shownPrice)}</div>
            <div className="text-xs text-black/55 dark:text-white/55">updated {lastUpdateEt || "-"}</div>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => setMode("daily")} className={`rounded-lg border px-2.5 py-1 text-xs ${mode === "daily" ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>Daily</button>
            <button type="button" onClick={() => setMode("intraday")} className={`rounded-lg border px-2.5 py-1 text-xs ${mode === "intraday" ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>Intraday</button>
          </div>
          <div className="flex items-center gap-2">
            {mode === "daily" ? [30, 90, 180, 365].map((d) => <button key={d} type="button" onClick={() => setDailyDays(d)} className={`rounded-lg border px-2.5 py-1 text-xs ${d === dailyDays ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>{d === 30 ? "1M" : d === 90 ? "3M" : d === 180 ? "6M" : "1Y"}</button>) : <>
              <button type="button" onClick={() => setSession("1D")} className={`rounded-lg border px-2.5 py-1 text-xs ${session === "1D" ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>1D</button>
              <button type="button" onClick={() => setSession("5D")} className={`rounded-lg border px-2.5 py-1 text-xs ${session === "5D" ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>5D</button>
              <button type="button" onClick={() => setResolution("1")} className={`rounded-lg border px-2.5 py-1 text-xs ${resolution === "1" ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>1m</button>
              <button type="button" onClick={() => setResolution("5")} className={`rounded-lg border px-2.5 py-1 text-xs ${resolution === "5" ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>5m</button>
            </>}
          </div>
          <button type="button" onClick={() => setCompareSpy((v) => !v)} className={`rounded-lg border px-2.5 py-1 text-xs ${compareSpy ? "border-emerald-500/40 bg-emerald-500/10" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>vs SPY</button>
        </div>
        <div className="mt-3 h-[20rem] rounded-xl border border-black/10 bg-white/70 p-2 dark:border-white/10 dark:bg-black/25 md:h-[22rem]">
          {points.length ? (
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full">
              <line x1="0" y1="12" x2="100" y2="12" stroke="rgba(100,116,139,0.16)" strokeWidth="0.32" />
              <line x1="0" y1="28" x2="100" y2="28" stroke="rgba(100,116,139,0.16)" strokeWidth="0.32" />
              <line x1="0" y1="44" x2="100" y2="44" stroke="rgba(100,116,139,0.16)" strokeWidth="0.32" />
              <line x1="0" y1="60" x2="100" y2="60" stroke="rgba(100,116,139,0.16)" strokeWidth="0.32" />
              <line x1="0" y1="78" x2="100" y2="78" stroke="rgba(100,116,139,0.12)" strokeWidth="0.28" />
              {points.map((p, i) => {
                const x = 1 + (i / Math.max(1, points.length - 1)) * 98;
                const yH = 76 - ((p.high - minLow) / priceRange) * 70;
                const yL = 76 - ((p.low - minLow) / priceRange) * 70;
                const yO = 76 - ((p.open - minLow) / priceRange) * 70;
                const yC = 76 - ((p.close - minLow) / priceRange) * 70;
                const up = p.close >= p.open;
                const top = Math.min(yO, yC);
                const h = Math.max(0.9, Math.abs(yO - yC));
                const vH = (p.volume / maxVolume) * 19;
                return (
                  <g key={`${p.day}-${i}`}>
                    <line x1={x} y1={yH} x2={x} y2={yL} stroke={up ? "#10b981" : "#e11d48"} strokeWidth={0.5} />
                    <rect x={x - candleW / 2} y={top} width={candleW} height={h} fill={up ? "#10b981" : "#e11d48"} opacity={0.9} />
                    <rect x={x - candleW / 2} y={100 - vH} width={candleW} height={vH} fill={up ? "rgba(16,185,129,0.32)" : "rgba(225,29,72,0.32)"} />
                  </g>
                );
              })}
              {compareSpy && spyLine ? <path d={spyLine} fill="none" stroke="#3b82f6" strokeWidth="0.8" strokeDasharray="1.2 1.2" /> : null}
            </svg>
          ) : loading ? <div className="flex h-full items-center justify-center text-sm text-black/55 dark:text-white/55">Loading chart...</div> : <div className="flex h-full items-center justify-center text-sm text-black/55 dark:text-white/55">Price history unavailable.</div>}
        </div>
      </Card>
      <Card>
        <div className="text-sm font-medium">Trade Decision</div>
        <div className="mt-2 grid gap-2 text-sm">
          <div className="rounded-lg border border-black/10 px-3 py-2 dark:border-white/10">
            <div className="text-xs text-black/55 dark:text-white/55">Signal</div>
            <div className="font-semibold">{tradeSignal}</div>
          </div>
          <div className="rounded-lg border border-black/10 px-3 py-2 dark:border-white/10">
            <div className="text-xs text-black/55 dark:text-white/55">Entry Zone</div>
            <div className="font-semibold tabular-nums">{fmtPrice(entry * 0.998)} - {fmtPrice(entry * 1.002)}</div>
          </div>
          <div className="rounded-lg border border-black/10 px-3 py-2 dark:border-white/10">
            <div className="text-xs text-black/55 dark:text-white/55">Stop Zone</div>
            <div className="font-semibold tabular-nums">{fmtPrice(stop * 0.998)} - {fmtPrice(stop * 1.002)}</div>
          </div>
          <div className="rounded-lg border border-black/10 px-3 py-2 dark:border-white/10">
            <div className="text-xs text-black/55 dark:text-white/55">Risk / Reward</div>
            <div className="font-semibold tabular-nums">1 : 1.8</div>
            <div className="mt-1 text-xs text-black/55 dark:text-white/55">Target {fmtPrice(target)}</div>
          </div>
          <div className="rounded-lg border border-black/10 px-3 py-2 text-sm dark:border-white/10">
            <div className="text-xs text-black/55 dark:text-white/55">Open / Prev Close</div>
            <div className="font-semibold tabular-nums">{fmtPrice(quoteDetail?.open)} / {fmtPrice(quoteDetail?.prev_close)}</div>
          </div>
        </div>
      </Card>
    </div>
  );
}
