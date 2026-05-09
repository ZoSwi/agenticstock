"use client";

import * as React from "react";

import { Shell } from "@/components/Shell";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import {
  deletePortfolioPosition,
  fetchAuditEvents,
  fetchPortfolioSummary,
  upsertPortfolioPosition,
  type AuditEvent,
  type PortfolioSummary,
} from "@/lib/api";

function fmtUsd(v: number | null | undefined): string {
  if (v == null) return "--";
  return Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(v);
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "--";
  return `${v > 0 ? "+" : ""}${(v * 100).toFixed(2)}%`;
}

export default function PortfolioPage() {
  const userId = "demo";
  const [summary, setSummary] = React.useState<PortfolioSummary | null>(null);
  const [events, setEvents] = React.useState<AuditEvent[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [ticker, setTicker] = React.useState("");
  const [quantity, setQuantity] = React.useState("");
  const [avgCost, setAvgCost] = React.useState("");

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, a] = await Promise.all([fetchPortfolioSummary(userId), fetchAuditEvents(userId, 30)]);
      setSummary(s);
      setEvents(a.events || []);
    } catch (e: any) {
      setError(e?.message || "Failed to load portfolio");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const totals = summary?.totals;
  const riskUsagePct = totals?.cost_basis ? Math.min(1, Math.abs(totals.unrealized_pl) / Math.max(1, totals.cost_basis)) : 0;

  return (
    <Shell>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Portfolio</h2>
          <p className="mt-1 text-sm text-black/60 dark:text-white/60">
            Live P/L, position book, and decision audit trail.
          </p>
        </div>
        <Button variant="secondary" onClick={refresh} disabled={loading}>
          Refresh
        </Button>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-4">
        <Card className="p-4">
          <div className="text-xs text-black/55 dark:text-white/55">Cost Basis</div>
          <div className="mt-1 text-lg font-semibold">{fmtUsd(totals?.cost_basis)}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-black/55 dark:text-white/55">Market Value</div>
          <div className="mt-1 text-lg font-semibold">{fmtUsd(totals?.market_value)}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-black/55 dark:text-white/55">Unrealized P/L</div>
          <div className={`mt-1 text-lg font-semibold ${((totals?.unrealized_pl || 0) >= 0) ? "text-emerald-600 dark:text-emerald-300" : "text-rose-600 dark:text-rose-300"}`}>
            {fmtUsd(totals?.unrealized_pl)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-black/55 dark:text-white/55">P/L %</div>
          <div className={`mt-1 text-lg font-semibold ${((totals?.unrealized_pl_pct || 0) >= 0) ? "text-emerald-600 dark:text-emerald-300" : "text-rose-600 dark:text-rose-300"}`}>
            {fmtPct(totals?.unrealized_pl_pct)}
          </div>
          <div className="mt-2 h-1.5 w-full rounded-full bg-black/10 dark:bg-white/10">
            <div className="h-full rounded-full bg-indigo-500/70" style={{ width: `${Math.round(riskUsagePct * 100)}%` }} />
          </div>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="text-sm font-medium">Positions</div>
          <div className="mt-3 grid gap-2 md:grid-cols-4">
            <Input value={ticker} onChange={(e) => setTicker(e.target.value)} placeholder="Ticker" />
            <Input value={quantity} onChange={(e) => setQuantity(e.target.value)} placeholder="Quantity" />
            <Input value={avgCost} onChange={(e) => setAvgCost(e.target.value)} placeholder="Avg Cost" />
            <Button
              onClick={async () => {
                const t = ticker.toUpperCase().trim();
                const q = Number(quantity);
                const c = Number(avgCost);
                if (!t || !Number.isFinite(q) || q <= 0 || !Number.isFinite(c) || c <= 0) return;
                setLoading(true);
                try {
                  await upsertPortfolioPosition({ user_id: userId, ticker: t, quantity: q, avg_cost: c });
                  setTicker("");
                  setQuantity("");
                  setAvgCost("");
                  await refresh();
                } catch (e: any) {
                  setError(e?.message || "Failed to save position");
                } finally {
                  setLoading(false);
                }
              }}
              disabled={loading}
            >
              Save
            </Button>
          </div>
          {error ? <div className="mt-3 text-sm text-rose-600">{error}</div> : null}
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-black/55 dark:text-white/55">
                  <th className="py-2">Ticker</th>
                  <th className="py-2">Qty</th>
                  <th className="py-2">Avg</th>
                  <th className="py-2">Last</th>
                  <th className="py-2">P/L</th>
                  <th className="py-2">P/L %</th>
                  <th className="py-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {(summary?.positions || []).map((p) => (
                  <tr key={p.ticker} className="border-t border-black/8 dark:border-white/10">
                    <td className="py-2 font-medium">{p.ticker}</td>
                    <td className="py-2">{p.quantity}</td>
                    <td className="py-2">{fmtUsd(p.avg_cost)}</td>
                    <td className="py-2">{fmtUsd(p.last_price)}</td>
                    <td className={`py-2 ${(p.unrealized_pl || 0) >= 0 ? "text-emerald-600 dark:text-emerald-300" : "text-rose-600 dark:text-rose-300"}`}>{fmtUsd(p.unrealized_pl)}</td>
                    <td className={`py-2 ${(p.unrealized_pl_pct || 0) >= 0 ? "text-emerald-600 dark:text-emerald-300" : "text-rose-600 dark:text-rose-300"}`}>{fmtPct(p.unrealized_pl_pct)}</td>
                    <td className="py-2">
                      <Button
                        variant="ghost"
                        onClick={async () => {
                          setLoading(true);
                          try {
                            await deletePortfolioPosition(userId, p.ticker);
                            await refresh();
                          } finally {
                            setLoading(false);
                          }
                        }}
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between gap-2">
            <div className="text-sm font-medium">Decision Audit</div>
            <Badge>{events.length}</Badge>
          </div>
          <div className="mt-3 space-y-2">
            {events.length ? (
              events.map((e) => (
                <div key={e.id} className="rounded-lg border border-black/10 px-3 py-2 text-sm dark:border-white/10">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold">{e.ticker}</span>
                    <Badge tone={e.risk_level === "high" ? "riskHigh" : e.risk_level === "medium" ? "riskMedium" : "riskLow"}>
                      {e.risk_level}
                    </Badge>
                  </div>
                  <div className="mt-1 text-black/70 dark:text-white/70">{e.decision}</div>
                  <div className="mt-1 text-xs text-black/55 dark:text-white/55">
                    confidence {(e.confidence_score * 100).toFixed(0)}% | {e.created_at ? e.created_at.replace("T", " ").replace("Z", " UTC") : "-"}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-black/60 dark:text-white/60">No audit events yet.</div>
            )}
          </div>
        </Card>
      </div>
    </Shell>
  );
}
