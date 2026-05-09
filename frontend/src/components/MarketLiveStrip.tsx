"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { getMarketStreamUrl, type MarketPulse } from "@/lib/api";

function fmtLatency(v: number | null | undefined): string {
  if (v == null) return "-";
  return `${v}ms`;
}

function fmtScore(v: number | undefined): string {
  if (v == null) return "-";
  return (v * 100).toFixed(0);
}

function fmtAsOfEt(v: string | undefined): string {
  if (!v) return "-";
  const m = v.match(/T(\d{2}:\d{2}:\d{2})/);
  if (m?.[1]) return `${m[1]} ET`;
  return v;
}

export function MarketLiveStrip({ initialPulse }: { initialPulse: MarketPulse }) {
  const [pulse, setPulse] = useState<MarketPulse>(initialPulse);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const es = new EventSource(getMarketStreamUrl(30, 12));
    const onPulse = (evt: MessageEvent) => {
      try {
        const next = JSON.parse(evt.data) as MarketPulse;
        setPulse(next);
        setConnected(true);
      } catch {
        // keep last pulse
      }
    };
    es.addEventListener("pulse", onPulse);
    es.onerror = () => {
      setConnected(false);
    };
    return () => {
      es.removeEventListener("pulse", onPulse);
      es.close();
    };
  }, []);

  const d = pulse.provider_diagnostics || {};
  const alpha = d.alphavantage;
  const finnhub = d.finnhub;
  const stooq = d.stooq;
  const yahoo = d.yahoo;

  return (
    <Card className="mt-4 border-black/12 bg-white/80 p-4 dark:border-white/12 dark:bg-black/25">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-black/65 dark:text-white/65">Feed Engine</div>
          <Badge tone={connected ? "bullish" : "riskMedium"}>{connected ? "connected" : "reconnecting"}</Badge>
          <Badge tone="riskMedium">delayed</Badge>
          {!!pulse.degraded_reason && <Badge tone="riskHigh">degraded</Badge>}
        </div>
        <div className="text-xs text-black/55 dark:text-white/55">
          source {pulse.data_source || "none"} | {pulse.universe_size} symbols | {fmtAsOfEt(pulse.as_of_et)}
        </div>
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-4">
        <div className="rounded-2xl border border-black/8 px-3 py-2 dark:border-white/12">
          <div className="text-xs text-black/55 dark:text-white/55">Alpha Vantage</div>
          <div className="mt-1 text-sm">score {fmtScore(alpha?.score)} | rows {alpha?.rows ?? 0} | {fmtLatency(alpha?.latency_ms)}</div>
        </div>
        <div className="rounded-2xl border border-black/8 px-3 py-2 dark:border-white/12">
          <div className="text-xs text-black/55 dark:text-white/55">Finnhub</div>
          <div className="mt-1 text-sm">score {fmtScore(finnhub?.score)} | rows {finnhub?.rows ?? 0} | {fmtLatency(finnhub?.latency_ms)}</div>
        </div>
        <div className="rounded-2xl border border-black/8 px-3 py-2 dark:border-white/12">
          <div className="text-xs text-black/55 dark:text-white/55">Stooq</div>
          <div className="mt-1 text-sm">score {fmtScore(stooq?.score)} | rows {stooq?.rows ?? 0} | {fmtLatency(stooq?.latency_ms)}</div>
        </div>
        <div className="rounded-2xl border border-black/8 px-3 py-2 dark:border-white/12">
          <div className="text-xs text-black/55 dark:text-white/55">Yahoo</div>
          <div className="mt-1 text-sm">score {fmtScore(yahoo?.score)} | rows {yahoo?.rows ?? 0} | {fmtLatency(yahoo?.latency_ms)}</div>
        </div>
      </div>
    </Card>
  );
}
