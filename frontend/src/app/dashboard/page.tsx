import Link from "next/link";

import { MarketLiveStrip } from "@/components/MarketLiveStrip";
import { Shell } from "@/components/Shell";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import {
  fetchLiveNews,
  fetchMarketPulse,
  type LiveNewsResponse,
  type MarketPulse,
  type MarketPulseRow,
} from "@/lib/api";

const focus = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "AMD", "MU", "AVGO", "NFLX"];

function formatAsOfEt(v?: string | null): string {
  if (!v) return "-";
  const m = v.match(/T(\d{2}:\d{2}:\d{2})/);
  return m?.[1] ? `${m[1]} ET` : v;
}

function formatAsOfUtc(v: string): string {
  const m = v.match(/T(\d{2}:\d{2}:\d{2})/);
  return m?.[1] ? `${m[1]} UTC` : v;
}

function fmtPct(v: number): string {
  return `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function fmtPrice(v: number): string {
  return Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(v);
}

function FlowPanel({ title, rows }: { title: string; rows: MarketPulseRow[] }) {
  return (
    <div>
      <div className="mb-2 text-sm font-medium">{title}</div>
      <div className="space-y-1.5">
        {rows.slice(0, 8).map((r) => (
          <Link
            key={`${title}-${r.ticker}`}
            href={`/stocks/${encodeURIComponent(r.ticker)}`}
            className="grid grid-cols-[1fr_auto_auto] items-center gap-2 rounded-lg border border-black/10 bg-white/70 px-3 py-2 text-sm hover:bg-white dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
          >
            <span className="font-medium">{r.ticker}</span>
            <span className="tabular-nums text-black/70 dark:text-white/70">{fmtPrice(r.last)}</span>
            <Badge tone={r.change_pct > 0 ? "bullish" : r.change_pct < 0 ? "bearish" : "neutral"}>{fmtPct(r.change_pct)}</Badge>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default async function DashboardPage() {
  let pulse: MarketPulse | null = null;
  let news: LiveNewsResponse | null = null;
  try {
    pulse = await fetchMarketPulse(20, false);
  } catch {
    pulse = null;
  }
  try {
    news = await fetchLiveNews(12);
  } catch {
    news = null;
  }

  const adv = pulse?.market_breadth?.advancers ?? 0;
  const dec = pulse?.market_breadth?.decliners ?? 0;
  const unc = pulse?.market_breadth?.unchanged ?? 0;
  const marketState = pulse?.market_status || "closed";
  const sessionLabel = marketState === "open" ? "regular session" : "after-hours / closed";

  return (
    <Shell>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Professional Market Dashboard</h2>
          <p className="mt-1 text-sm text-black/60 dark:text-white/60">
            Live market flow, after-hours context, and decision-ready watch panels.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={marketState === "open" ? "bullish" : "riskMedium"}>{sessionLabel}</Badge>
          <Badge>{pulse?.stale ? "cached snapshot" : "live snapshot"}</Badge>
          <Badge>{formatAsOfEt(pulse?.as_of_et)}</Badge>
        </div>
      </div>

      {pulse ? <MarketLiveStrip initialPulse={pulse} /> : null}

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-black/10 bg-white/70 px-3 py-3 dark:border-white/10 dark:bg-white/5">
              <div className="text-xs text-black/55 dark:text-white/55">Advancers</div>
              <div className="mt-1 text-xl font-semibold text-emerald-600 dark:text-emerald-300">{adv}</div>
            </div>
            <div className="rounded-lg border border-black/10 bg-white/70 px-3 py-3 dark:border-white/10 dark:bg-white/5">
              <div className="text-xs text-black/55 dark:text-white/55">Decliners</div>
              <div className="mt-1 text-xl font-semibold text-rose-600 dark:text-rose-300">{dec}</div>
            </div>
            <div className="rounded-lg border border-black/10 bg-white/70 px-3 py-3 dark:border-white/10 dark:bg-white/5">
              <div className="text-xs text-black/55 dark:text-white/55">Unchanged</div>
              <div className="mt-1 text-xl font-semibold">{unc}</div>
            </div>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <FlowPanel title="Top Gainers" rows={pulse?.top_gainers || []} />
            <FlowPanel title="Top Losers" rows={pulse?.top_losers || []} />
            <FlowPanel title="Most Active" rows={pulse?.most_active || []} />
          </div>
        </Card>

        <Card>
          <div className="text-sm font-medium">Focus Board</div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {focus.map((t) => (
              <Link
                key={t}
                href={`/stocks/${t}`}
                className="rounded-lg border border-black/10 bg-white/70 px-3 py-2 text-sm hover:bg-white dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
              >
                {t}
              </Link>
            ))}
          </div>
          <div className="mt-4 text-xs text-black/55 dark:text-white/55">
            Use stock pages for full risk engine, scenario P/L, and AI professional outcome.
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="flex items-center justify-between gap-2">
            <div className="text-sm font-medium">Macro Regime Notes</div>
            <Badge tone="riskMedium">rate-sensitive market</Badge>
          </div>
          <div className="mt-3 grid gap-2 text-sm text-black/70 dark:text-white/70">
            <div className="rounded-lg border border-black/10 bg-white/70 px-3 py-2 dark:border-white/10 dark:bg-white/5">
              Keep gross exposure controlled in high-volatility sessions.
            </div>
            <div className="rounded-lg border border-black/10 bg-white/70 px-3 py-2 dark:border-white/10 dark:bg-white/5">
              Favor staggered entries and tighter loss budgets after large momentum gaps.
            </div>
            <div className="rounded-lg border border-black/10 bg-white/70 px-3 py-2 dark:border-white/10 dark:bg-white/5">
              Re-check event risk before open: earnings, CPI, Fed speakers, guidance revisions.
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between gap-2">
            <div className="text-sm font-medium">Live Headlines</div>
            <Badge>{news?.degraded ? "degraded" : "live"}</Badge>
          </div>
          <div className="mt-3 grid gap-2">
            {(news?.headlines || []).slice(0, 7).map((h) => (
              <a
                key={`${h.url}-${h.published_at}`}
                href={h.url}
                target="_blank"
                rel="noreferrer"
                className="block rounded-lg border border-black/10 bg-white/70 px-3 py-2 text-sm hover:bg-white dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
              >
                <div className="line-clamp-2">{h.title}</div>
                <div className="mt-1 text-xs text-black/50 dark:text-white/50">
                  {h.source} | {formatAsOfUtc(h.published_at)}
                </div>
              </a>
            ))}
          </div>
        </Card>
      </div>
    </Shell>
  );
}
