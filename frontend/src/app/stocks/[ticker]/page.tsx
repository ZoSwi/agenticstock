import Link from "next/link";

import { Shell } from "@/components/Shell";
import { StockContextPanel } from "@/components/StockContextPanel";
import { StockLivePanel } from "@/components/StockLivePanel";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import type { AnalystView, LiveNewsResponse, StockAnalysis, StockSignals } from "@/lib/api";

async function fetchAnalysisServer(ticker: string): Promise<StockAnalysis | null> {
  const base =
    process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://backend:8000";
  try {
    const res = await fetch(`${base}/stocks/${encodeURIComponent(ticker)}/analysis`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as StockAnalysis;
  } catch {
    return null;
  }
}

async function fetchSignalsServer(ticker: string): Promise<StockSignals | null> {
  const base =
    process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://backend:8000";
  try {
    const res = await fetch(`${base}/stocks/${encodeURIComponent(ticker)}/signals`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as StockSignals;
  } catch {
    return null;
  }
}

async function fetchTickerNewsServer(ticker: string, limit: number = 8): Promise<(LiveNewsResponse & { ticker: string }) | null> {
  const base = process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://backend:8000";
  try {
    const res = await fetch(`${base}/news/${encodeURIComponent(ticker)}?limit=${Math.max(5, Math.min(60, limit))}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as LiveNewsResponse & { ticker: string };
  } catch {
    return null;
  }
}

async function fetchTickerDisplayNameServer(ticker: string): Promise<string | null> {
  const base = process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://backend:8000";
  try {
    const res = await fetch(`${base}/stocks/search?q=${encodeURIComponent(ticker)}&limit=8`, { cache: "no-store" });
    if (res.ok) {
      const payload = (await res.json()) as { results?: Array<{ ticker: string; name?: string | null }> };
      const exact = (payload.results || []).find((r) => (r.ticker || "").toUpperCase() === ticker.toUpperCase());
      if (exact?.name) return exact.name;
    }
    const p = await fetch(`${base}/stocks/${encodeURIComponent(ticker)}/profile`, { cache: "no-store" });
    if (!p.ok) return null;
    const prof = (await p.json()) as { name?: string | null };
    return prof.name || null;
  } catch {
    return null;
  }
}

async function fetchAnalystViewServer(ticker: string): Promise<AnalystView | null> {
  const base = process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://backend:8000";
  try {
    const res = await fetch(`${base}/stocks/${encodeURIComponent(ticker)}/analyst-view`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as AnalystView;
  } catch {
    return null;
  }
}

function toneOutlook(outlook: StockAnalysis["outlook"]) {
  if (outlook === "bullish") return "bullish";
  if (outlook === "bearish") return "bearish";
  return "neutral";
}

function toneRisk(risk: StockAnalysis["risk_level"]) {
  if (risk === "high") return "riskHigh";
  if (risk === "medium") return "riskMedium";
  return "riskLow";
}

function formatAsOfUtc(v: string): string {
  const m = v.match(/T(\d{2}:\d{2}:\d{2})/);
  if (m?.[1]) return `${m[1]} UTC`;
  return v;
}

export default async function StockDetailPage({ params }: { params: { ticker: string } | Promise<{ ticker: string }> }) {
  const resolved = await Promise.resolve(params as { ticker: string } | Promise<{ ticker: string }>);
  const ticker = (resolved?.ticker || "").toUpperCase().trim();
  if (!ticker) {
    return (
      <Shell>
        <Card>
          <div className="text-base font-semibold">Invalid ticker</div>
          <p className="mt-2 text-sm text-black/60 dark:text-white/60">
            The stock symbol in the URL is missing or invalid.
          </p>
          <div className="mt-4">
            <Link
              href="/"
              className="inline-block rounded-full border border-black/10 bg-white/60 px-4 py-2 text-sm hover:bg-white dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
            >
              Back to Home
            </Link>
          </div>
        </Card>
      </Shell>
    );
  }
  const [a, s, news, displayName, analyst] = await Promise.all([
    fetchAnalysisServer(ticker),
    fetchSignalsServer(ticker),
    fetchTickerNewsServer(ticker, 8),
    fetchTickerDisplayNameServer(ticker),
    fetchAnalystViewServer(ticker),
  ]);
  if (!a) {
    return (
      <Shell>
        <Card>
          <div className="text-base font-semibold">Stock data temporarily unavailable</div>
          <p className="mt-2 text-sm text-black/60 dark:text-white/60">
            We could not load analysis for {ticker.toUpperCase()} right now. Please retry in a few moments.
          </p>
          <div className="mt-4">
            <Link
              href="/"
              className="inline-block rounded-full border border-black/10 bg-white/60 px-4 py-2 text-sm hover:bg-white dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
            >
              Back to Home
            </Link>
          </div>
        </Card>
      </Shell>
    );
  }

  return (
    <Shell>
      <StockLivePanel ticker={a.ticker} />
      <StockContextPanel ticker={a.ticker} initialAnalysis={a} initialSignals={s} initialNews={news} initialAnalyst={analyst} />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">{a.ticker}</h2>
          {displayName ? <p className="mt-1 text-sm text-black/55 dark:text-white/55">{displayName}</p> : null}
          <p className="mt-1 text-sm text-black/60 dark:text-white/60">
            Directional outlook with reasons, risks, and what to do next.
          </p>
          {a.model_status?.degraded ? (
            <div className="mt-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
              Live model status: degraded. {a.model_status.reason || "Using conservative fallback until provider recovers."}
            </div>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={toneOutlook(a.outlook) as any}>{a.outlook}</Badge>
          <Badge tone={toneRisk(a.risk_level) as any}>risk: {a.risk_level}</Badge>
          <Badge>{a.confidence_score.toFixed(2)} confidence</Badge>
          <Badge>{a.model_status?.source || "unknown"}</Badge>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="text-sm font-medium">Summary</div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <Card className="p-4">
              <div className="text-xs text-black/60 dark:text-white/60">Growth probability</div>
              <div className="mt-1 text-2xl font-semibold">{Math.round(a.rise_probability * 100)}%</div>
            </Card>
            <Card className="p-4">
              <div className="text-xs text-black/60 dark:text-white/60">Fall risk</div>
              <div className="mt-1 text-2xl font-semibold">{Math.round(a.fall_probability * 100)}%</div>
            </Card>
            <Card className="p-4">
              <div className="text-xs text-black/60 dark:text-white/60">Volatility</div>
              <div className="mt-1 text-2xl font-semibold">{a.volatility_detected ? "High" : "Normal"}</div>
            </Card>
          </div>

          {s ? (
            <Card className="mt-4 border-black/10 bg-white/70 p-4 dark:border-white/10 dark:bg-black/20">
              <div className="text-sm font-medium">Nowcast & Forecast</div>
              <div className="mt-2 grid gap-2 text-sm text-black/70 dark:text-white/70 md:grid-cols-2">
                <div>
                  Regime: <span className="font-semibold">{s.nowcast.regime}</span> | Risk:{" "}
                  <span className="font-semibold">{s.nowcast.risk_level}</span>
                </div>
                <div>
                  1D: <span className="font-semibold">{s.forecast.horizon_1d}</span> | 5D:{" "}
                  <span className="font-semibold">{s.forecast.horizon_5d}</span> | 20D:{" "}
                  <span className="font-semibold">{s.forecast.horizon_20d}</span>
                </div>
              </div>
              <div className="mt-2 text-xs text-black/55 dark:text-white/55">
                {s.current_update.quote
                  ? `Quote ${s.current_update.quote.ticker}: ${s.current_update.quote.last} (${s.current_update.quote.change_pct.toFixed(2)}%)`
                  : "Quote unavailable in current pulse window."}
              </div>
            </Card>
          ) : null}

          {a.model_status?.degraded ? (
            <Card className="mt-6 border-amber-500/30 bg-amber-500/10">
              <div className="text-sm font-medium">Model Degraded</div>
              <p className="mt-2 text-sm text-black/70 dark:text-white/70">
                Live predictive factors are temporarily unavailable. Signals shown above are conservative defaults while
                data providers recover.
              </p>
            </Card>
          ) : (
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div>
                <div className="text-sm font-medium">Why it may rise</div>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-black/70 dark:text-white/70">
                  {a.growth_drivers.slice(0, 6).map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="text-sm font-medium">Why it may fall</div>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-black/70 dark:text-white/70">
                  {a.fall_drivers.slice(0, 6).map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </Card>

        <Card>
          <div className="text-sm font-medium">Guidance</div>
          <div className="mt-2 text-sm text-black/60 dark:text-white/60">Suggested action</div>
          <div className="mt-1 text-xl font-semibold">{a.suggested_action}</div>

          <div className="mt-5 text-sm font-medium">Time horizon</div>
          <div className="mt-2 grid gap-2 text-sm text-black/70 dark:text-white/70">
            <div className="flex items-center justify-between">
              <span>Short-term</span>
              <Badge tone={toneOutlook(a.time_horizon.short_term as any) as any}>{a.time_horizon.short_term}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Medium-term</span>
              <Badge tone={toneOutlook(a.time_horizon.medium_term as any) as any}>{a.time_horizon.medium_term}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Long-term</span>
              <Badge tone={toneOutlook(a.time_horizon.long_term as any) as any}>{a.time_horizon.long_term}</Badge>
            </div>
          </div>

          <div className="mt-5 text-sm font-medium">Watch next</div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-black/70 dark:text-white/70">
            {a.watch_next.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>

          <div className="mt-5 flex items-center justify-between gap-2 text-sm font-medium">
            <span>Live headlines</span>
            <Badge>{news?.degraded ? "degraded" : "live"}</Badge>
          </div>
          <div className="mt-2 grid gap-2">
            {(news?.headlines || []).slice(0, 5).map((h) => (
              <a
                key={`${h.url}-${h.published_at}`}
                href={h.url}
                target="_blank"
                rel="noreferrer"
                className="block rounded-lg border border-black/10 px-3 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/5"
              >
                <div className="line-clamp-2">{h.title}</div>
                <div className="mt-1 text-xs text-black/50 dark:text-white/50">
                  {h.source} | {formatAsOfUtc(h.published_at)}
                </div>
              </a>
            ))}
          </div>

          <div className="mt-6 text-xs text-black/50 dark:text-white/50">
            Not financial advice. Probabilities are estimates.
          </div>

          <div className="mt-5 flex gap-2">
            <Link
              href={`/compare?t=${encodeURIComponent(a.ticker)}`}
              className="w-full rounded-full border border-black/10 bg-white/60 px-4 py-2 text-center text-sm hover:bg-white dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
            >
              Compare
            </Link>
            <Link
              href={`/chat?q=${encodeURIComponent(`Should I invest in ${a.ticker}?`)}`}
              className="w-full rounded-full bg-black px-4 py-2 text-center text-sm font-medium text-white hover:bg-black/85 dark:bg-white dark:text-black dark:hover:bg-white/85"
            >
              Ask AI
            </Link>
          </div>
        </Card>
      </div>
    </Shell>
  );
}
