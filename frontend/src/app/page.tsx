import Link from "next/link";

import { Shell } from "@/components/Shell";
import { TickerSearch } from "@/components/TickerSearch";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { MarketLiveStrip } from "@/components/MarketLiveStrip";
import { fetchMarketPulse, type MarketPulse, type MarketPulseIndex, type MarketPulseRow } from "@/lib/api";

function pctTone(v: number): "bullish" | "bearish" | "neutral" {
  if (v > 0) return "bullish";
  if (v < 0) return "bearish";
  return "neutral";
}

function formatPct(v: number): string {
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function formatDelta(v: number): string {
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}`;
}

function formatPrice(v: number): string {
  return Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(v);
}

function formatVolume(v: number): string {
  return Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(v);
}

function formatAsOfEt(v: string): string {
  const m = v.match(/T(\d{2}:\d{2}:\d{2})/);
  if (m?.[1]) return `${m[1]} ET`;
  return v;
}

function FlowList({ title, rows }: { title: string; rows: MarketPulseRow[] }) {
  return (
    <Card className="h-full border-black/15 bg-white/75 dark:border-white/15 dark:bg-white/5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-black/65 dark:text-white/65">{title}</h3>
        <span className="text-xs text-black/45 dark:text-white/45">{rows.length} symbols</span>
      </div>
      <div className="space-y-2">
        {rows.map((r, i) => (
          <Link
            key={r.ticker}
            href={`/stocks/${encodeURIComponent(r.ticker)}`}
            className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-3 rounded-2xl border border-black/6 bg-white/80 px-3 py-2.5 transition hover:border-black/15 hover:shadow-sm dark:border-white/10 dark:bg-black/25 dark:hover:border-white/20"
          >
            <div className="w-6 text-center text-xs font-semibold tabular-nums text-black/50 dark:text-white/50">{i + 1}</div>
            <div>
              <div className="text-sm font-semibold tracking-tight">{r.ticker}</div>
              <div className="mt-1 h-1.5 w-20 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
                <div
                  className={r.change_pct >= 0 ? "h-full bg-emerald-500/80" : "h-full bg-rose-500/80"}
                  style={{ width: `${Math.min(100, Math.max(6, Math.abs(r.change_pct) * 9))}%` }}
                />
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium tabular-nums">{formatPrice(r.last)}</div>
              <div className="text-xs tabular-nums text-black/50 dark:text-white/50">
                {formatDelta(r.change)} | Vol {formatVolume(r.volume)}
              </div>
            </div>
            <Badge tone={pctTone(r.change_pct)} className="justify-center tabular-nums">
              {formatPct(r.change_pct)}
            </Badge>
          </Link>
        ))}
      </div>
    </Card>
  );
}

function StatCard({ label, value, tone }: { label: string; value: number; tone: "bullish" | "bearish" | "neutral" }) {
  const toneClass =
    tone === "bullish"
      ? "text-emerald-700 dark:text-emerald-300"
      : tone === "bearish"
        ? "text-rose-700 dark:text-rose-300"
        : "text-black/80 dark:text-white/80";
  return (
    <Card className="border-black/10 bg-white/80 p-4 dark:border-white/10 dark:bg-black/20">
      <div className="text-xs uppercase tracking-[0.12em] text-black/55 dark:text-white/55">{label}</div>
      <div className={`mt-2 text-2xl font-semibold tabular-nums ${toneClass}`}>{value}</div>
    </Card>
  );
}

function IndexStrip({ rows }: { rows: MarketPulseIndex[] }) {
  const desired = [
    { name: "S&P 500", symbol: "^GSPC", proxy: "SPY" },
    { name: "Nasdaq", symbol: "^IXIC", proxy: "QQQ" },
    { name: "Dow 30", symbol: "^DJI", proxy: "DIA" },
    { name: "Russell 2000", symbol: "^RUT", proxy: "IWM" },
    { name: "VIX", symbol: "^VIX", proxy: "VIXY" },
  ];
  const bySymbol = new Map(rows.map((r) => [r.symbol, r]));
  const board = desired.map((d) => ({ ...d, row: bySymbol.get(d.symbol) || bySymbol.get(d.proxy) || null }));

  return (
    <div className="grid gap-3 md:grid-cols-5">
      {board.map((idx) => (
        <Card key={idx.symbol} className="border-black/10 bg-white/85 p-4 shadow-sm dark:border-white/10 dark:bg-black/25">
          <div className="flex items-center justify-between gap-2">
            <div className="text-xs uppercase tracking-[0.12em] text-black/55 dark:text-white/55">{idx.name}</div>
            <div className="text-[10px] text-black/45 dark:text-white/45">{idx.row?.symbol || idx.symbol}</div>
          </div>
          {idx.row ? (
            <>
              <div className="mt-1 text-xl font-semibold tabular-nums">{idx.row.last.toFixed(2)}</div>
              <div className="mt-1 text-sm tabular-nums">
                <span className={idx.row.change_pct >= 0 ? "text-emerald-600 dark:text-emerald-300" : "text-rose-600 dark:text-rose-300"}>
                  {formatDelta(idx.row.change)} ({formatPct(idx.row.change_pct)})
                </span>
              </div>
            </>
          ) : (
            <>
              <div className="mt-1 text-xl font-semibold tabular-nums text-black/35 dark:text-white/35">--</div>
              <div className="mt-1 text-xs text-black/45 dark:text-white/45">waiting for live feed</div>
            </>
          )}
        </Card>
      ))}
    </div>
  );
}

async function HomePulse() {
  let pulse: MarketPulse | null = null;
  try {
    pulse = await fetchMarketPulse(20, false);
  } catch {
    pulse = null;
  }

  if (!pulse) {
    return (
      <Card>
        <div className="text-base font-semibold">Market Feed Warming Up</div>
        <p className="mt-2 text-sm text-black/60 dark:text-white/60">
          The app is online. Data provider cache is warming and last snapshot will appear shortly.
        </p>
      </Card>
    );
  }
  if (pulse.universe_size === 0) {
    return (
      <Card>
        <div className="text-base font-semibold">Live Feed Warming Up</div>
        <p className="mt-2 text-sm text-black/60 dark:text-white/60">
          Providers are returning limited payloads. Trigger a pipeline refresh and retry in one minute.
        </p>
      </Card>
    );
  }

  const adv = pulse.market_breadth?.advancers ?? 0;
  const dec = pulse.market_breadth?.decliners ?? 0;
  const unc = pulse.market_breadth?.unchanged ?? 0;
  const providers = pulse.provider_status ?? { finnhub: false, alphavantage: false, stooq: false, yahoo: false };

  return (
    <section className="mt-8 space-y-4">
      <MarketLiveStrip initialPulse={pulse} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold tracking-tight">Market Pulse</h2>
          <Badge tone={pulse.market_status === "open" ? "bullish" : "neutral"}>{pulse.market_status}</Badge>
          <Badge>US Equities</Badge>
          <Badge>NYSE / Nasdaq</Badge>
          <Badge tone="riskMedium">Delayed feed</Badge>
          {pulse.stale && <Badge tone="riskMedium">Last known snapshot</Badge>}
          <Badge tone={providers.finnhub ? "bullish" : "neutral"}>Finnhub</Badge>
          <Badge tone={providers.alphavantage ? "bullish" : "neutral"}>Alpha Vantage</Badge>
          <Badge tone={providers.stooq ? "bullish" : "neutral"}>Stooq</Badge>
          <Badge tone={providers.yahoo ? "bullish" : "neutral"}>Yahoo</Badge>
        </div>
        <div className="text-xs text-black/55 dark:text-white/55">
          {pulse.universe_size} tracked | source {pulse.data_source || "unknown"} | updated{" "}
          {formatAsOfEt(pulse.as_of_et)}
        </div>
      </div>

      <IndexStrip rows={pulse.indices} />

      <div className="grid gap-3 md:grid-cols-3">
        <StatCard label="Advancers" value={adv} tone="bullish" />
        <StatCard label="Decliners" value={dec} tone="bearish" />
        <StatCard label="Unchanged" value={unc} tone="neutral" />
      </div>

      {!!pulse.sector_leaders?.length && (
        <Card className="border-black/12 bg-white/80 dark:border-white/12 dark:bg-black/20">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-black/65 dark:text-white/65">Sector Leaders</h3>
            <span className="text-xs text-black/45 dark:text-white/45">ETF rotation view</span>
          </div>
          <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4">
            {pulse.sector_leaders.map((s) => (
              <div key={s.symbol} className="rounded-2xl border border-black/7 bg-white/75 px-3 py-3 dark:border-white/10 dark:bg-black/20">
                <div className="text-xs text-black/55 dark:text-white/55">{s.name}</div>
                <div className="mt-1 text-sm font-semibold tabular-nums">{s.symbol}</div>
                <div className={s.change_pct >= 0 ? "mt-1 text-sm text-emerald-600 dark:text-emerald-300" : "mt-1 text-sm text-rose-600 dark:text-rose-300"}>
                  {formatPct(s.change_pct)}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <FlowList title="Top Gainers" rows={pulse.top_gainers} />
        <FlowList title="Top Losers" rows={pulse.top_losers} />
        <FlowList title="Most Active" rows={pulse.most_active} />
      </div>
    </section>
  );
}

export default async function Home() {
  return (
    <Shell>
      <div className="overflow-hidden">
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr] lg:items-start">
          <Card className="border-black/20 bg-white/80 p-7 shadow-md dark:border-white/20 dark:bg-black/35">
            <div className="flex flex-wrap items-center gap-2">
              <Badge>Market Dashboard</Badge>
              <Badge>Single Web UI</Badge>
              <Badge>Risk Signals</Badge>
              <Badge>AI Narratives</Badge>
            </div>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight md:text-5xl">CEO Market Terminal</h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-black/65 dark:text-white/65">
              Desktop-first stock workspace for scanning market breadth, sector rotation, and AI-supported decision flow.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/dashboard">
                <Button>Open Dashboard</Button>
              </Link>
              <Link href="/compare">
                <Button variant="secondary">Compare Stocks</Button>
              </Link>
              <Link href="/watchlist">
                <Button variant="ghost">Watchlist</Button>
              </Link>
            </div>
          </Card>

          <Card className="border-black/15 bg-white/80 p-6 shadow-sm dark:border-white/15 dark:bg-black/25">
            <div className="text-sm font-semibold uppercase tracking-[0.1em] text-black/70 dark:text-white/70">Analyze a ticker</div>
            <div className="mt-2 text-sm text-black/60 dark:text-white/60">
              Search any symbol and open a complete view with outlook, drivers, volatility risk, and action framing.
            </div>
            <div className="mt-4">
              <TickerSearch />
            </div>
            <div className="mt-5 rounded-2xl border border-black/8 bg-white/70 p-3 text-xs text-black/55 dark:border-white/10 dark:bg-black/25 dark:text-white/55">
              Budget mode: delayed quotes and bounded refresh intervals are enabled to keep response time stable.
            </div>
          </Card>
        </div>

        <HomePulse />
      </div>
    </Shell>
  );
}
