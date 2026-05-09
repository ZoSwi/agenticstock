"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import {
  createAuditEvent,
  fetchAnalystView,
  fetchAnalysis,
  fetchSignals,
  fetchTickerNews,
  fetchStockAiOutcome,
  type AnalystView,
  type LiveNewsResponse,
  type StockAnalysis,
  type StockAiOutcome,
  type StockSignals,
} from "@/lib/api";

function fmtClock(v?: string | null): string {
  if (!v) return "-";
  const m = v.match(/T(\d{2}:\d{2}:\d{2})/);
  return m?.[1] ? `${m[1]} ET` : v;
}

export function StockContextPanel({
  ticker,
  initialAnalysis,
  initialSignals,
  initialNews,
  initialAnalyst,
}: {
  ticker: string;
  initialAnalysis: StockAnalysis;
  initialSignals: StockSignals | null;
  initialNews: (LiveNewsResponse & { ticker: string }) | null;
  initialAnalyst: AnalystView | null;
}) {
  const [analysis, setAnalysis] = useState(initialAnalysis);
  const [signals, setSignals] = useState(initialSignals);
  const [news, setNews] = useState(initialNews);
  const [analyst, setAnalyst] = useState<AnalystView | null>(initialAnalyst);
  const [aiAnswer, setAiAnswer] = useState<string>("");
  const [aiOutcome, setAiOutcome] = useState<StockAiOutcome | null>(null);
  const [aiLive, setAiLive] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [lastAuditKey, setLastAuditKey] = useState("");
  const [tab, setTab] = useState<"plan" | "scenarios" | "drivers" | "news">("plan");
  const [showRationale, setShowRationale] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const pull = async () => {
      try {
        const [a, s, n, av] = await Promise.all([
          fetchAnalysis(ticker),
          fetchSignals(ticker),
          fetchTickerNews(ticker, 8),
          fetchAnalystView(ticker),
        ]);
        if (cancelled) return;
        setAnalysis(a);
        setSignals(s);
        setNews(n);
        setAnalyst(av);
      } catch {
        // keep previous
      }
    };
    void pull();
    const quoteTimer = setInterval(() => {
      void fetchSignals(ticker).then((s) => !cancelled && setSignals(s)).catch(() => {});
      void fetchAnalysis(ticker).then((a) => !cancelled && setAnalysis(a)).catch(() => {});
    }, 30000);
    const newsTimer = setInterval(() => {
      void fetchTickerNews(ticker, 8).then((n) => !cancelled && setNews(n)).catch(() => {});
      void fetchAnalystView(ticker).then((av) => !cancelled && setAnalyst(av)).catch(() => {});
    }, 90000);
    return () => {
      cancelled = true;
      clearInterval(quoteTimer);
      clearInterval(newsTimer);
    };
  }, [ticker]);

  useEffect(() => {
    if (!aiOutcome?.decision) return;
    const key = `${ticker}:${aiOutcome.decision.action}:${aiOutcome.decision.confidence_score.toFixed(4)}:${aiOutcome.decision.risk_level}`;
    if (key === lastAuditKey) return;
    setLastAuditKey(key);
    void createAuditEvent({
      user_id: "demo",
      ticker,
      decision: aiOutcome.decision.action,
      confidence_score: aiOutcome.decision.confidence_score,
      risk_level: aiOutcome.decision.risk_level,
      source: "stock_ai_outcome",
    }).catch(() => {});
  }, [aiOutcome, lastAuditKey, ticker]);

  useEffect(() => {
    let cancelled = false;
    const ask = async () => {
      setAiLoading(true);
      try {
        const res = await fetchStockAiOutcome(ticker, "advanced");
        if (cancelled) return;
        setAiOutcome(res);
        setAiAnswer(res.answer_markdown || "");
        setAiLive(!res.degraded);
      } catch {
        if (cancelled) return;
        setAiLive(false);
      } finally {
        if (!cancelled) setAiLoading(false);
      }
    };
    void ask();
    const timer = setInterval(() => {
      void ask();
    }, 90000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [ticker]);

  return (
    <div className="mt-4 grid gap-4 xl:grid-cols-[1.6fr_1fr]">
      <Card>
        <div className="flex items-center justify-between gap-2">
          <div className="text-sm font-medium">Professional Outcome</div>
          <Badge tone={aiLive ? "bullish" : "riskMedium"}>{aiLoading ? "updating" : aiLive ? "live" : "degraded"}</Badge>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-5">
          <Card className="p-2.5"><div className="text-[11px] text-black/55 dark:text-white/55">Action</div><div className="text-sm font-semibold">{aiOutcome?.decision.action || "-"}</div></Card>
          <Card className="p-2.5"><div className="text-[11px] text-black/55 dark:text-white/55">Bias</div><div className="text-sm font-semibold">{aiOutcome?.decision.bias || analysis.outlook}</div></Card>
          <Card className="p-2.5"><div className="text-[11px] text-black/55 dark:text-white/55">Confidence</div><div className="text-sm font-semibold">{aiOutcome ? `${(aiOutcome.decision.confidence_score * 100).toFixed(0)}%` : `${Math.round(analysis.confidence_score * 100)}%`}</div></Card>
          <Card className="p-2.5"><div className="text-[11px] text-black/55 dark:text-white/55">Risk</div><div className="text-sm font-semibold">{aiOutcome?.decision.risk_level || analysis.risk_level}</div></Card>
          <Card className="p-2.5"><div className="text-[11px] text-black/55 dark:text-white/55">Exp 20D</div><div className="text-sm font-semibold">{aiOutcome ? `${(aiOutcome.decision.expected_return_20d * 100).toFixed(2)}%` : "-"}</div></Card>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" onClick={() => setTab("plan")} className={`rounded-lg border px-2.5 py-1 text-xs ${tab === "plan" ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>Trade Plan</button>
          <button type="button" onClick={() => setTab("scenarios")} className={`rounded-lg border px-2.5 py-1 text-xs ${tab === "scenarios" ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>Scenarios</button>
          <button type="button" onClick={() => setTab("drivers")} className={`rounded-lg border px-2.5 py-1 text-xs ${tab === "drivers" ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>Drivers</button>
          <button type="button" onClick={() => setTab("news")} className={`rounded-lg border px-2.5 py-1 text-xs ${tab === "news" ? "border-black/25 bg-black text-white dark:border-white/25 dark:bg-white dark:text-black" : "border-black/10 bg-white/60 dark:border-white/10 dark:bg-white/5"}`}>News</button>
          <button type="button" onClick={() => setShowRationale((v) => !v)} className="ml-auto rounded-lg border border-black/10 bg-white/60 px-2.5 py-1 text-xs dark:border-white/10 dark:bg-white/5">
            {showRationale ? "Hide AI Rationale" : "View Full AI Rationale"}
          </button>
        </div>

        {tab === "plan" ? (
          <div className="mt-3 grid gap-2 md:grid-cols-4 text-sm">
            <Card className="p-3"><div className="text-xs text-black/55 dark:text-white/55">Entry</div><div className="font-semibold">{aiOutcome?.trade_plan.entry_style || "-"}</div></Card>
            <Card className="p-3"><div className="text-xs text-black/55 dark:text-white/55">Stop</div><div className="font-semibold">{aiOutcome ? `${aiOutcome.trade_plan.stop_loss_pct.toFixed(2)}%` : "-"}</div></Card>
            <Card className="p-3"><div className="text-xs text-black/55 dark:text-white/55">Target</div><div className="font-semibold">{aiOutcome ? `${aiOutcome.trade_plan.target_pct.toFixed(2)}%` : "-"}</div></Card>
            <Card className="p-3"><div className="text-xs text-black/55 dark:text-white/55">R/R</div><div className="font-semibold">{aiOutcome ? aiOutcome.trade_plan.risk_reward_ratio.toFixed(2) : "-"}</div></Card>
          </div>
        ) : null}
        {tab === "scenarios" ? (
          <Card className="mt-3 p-3 text-sm">
            <div className="grid gap-1">
              {(aiOutcome?.scenarios_20d || []).map((s) => (
                <div key={s.name} className="flex items-center justify-between">
                  <span className="uppercase">{s.name}</span>
                  <span>{(s.probability * 100).toFixed(0)}% | {s.return_pct > 0 ? "+" : ""}{s.return_pct.toFixed(2)}%</span>
                </div>
              ))}
            </div>
          </Card>
        ) : null}
        {tab === "drivers" ? (
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <Card className="p-3">
              <div className="text-sm font-medium">Growth Drivers</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-black/70 dark:text-white/70">
                {analysis.growth_drivers.slice(0, 3).map((d) => <li key={d}>{d}</li>)}
              </ul>
            </Card>
            <Card className="p-3">
              <div className="text-sm font-medium">Risk Drivers</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-black/70 dark:text-white/70">
                {analysis.fall_drivers.slice(0, 3).map((d) => <li key={d}>{d}</li>)}
              </ul>
            </Card>
          </div>
        ) : null}
        {tab === "news" ? (
          <Card className="mt-3 p-3">
            <div className="grid gap-2">
              {(news?.headlines || []).slice(0, 4).map((h) => (
                <a key={`${h.url}-${h.published_at}`} href={h.url} target="_blank" rel="noreferrer" className="block rounded-lg border border-black/10 px-3 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/5">
                  <div className="line-clamp-2">{h.title}</div>
                  <div className="mt-1 text-xs text-black/50 dark:text-white/50">{h.source} | {h.published_at.replace("T", " ").replace("Z", " UTC")}</div>
                </a>
              ))}
            </div>
          </Card>
        ) : null}

        {showRationale ? (
          <div className="prose mt-3 max-w-none text-sm prose-p:leading-7 dark:prose-invert">
            {aiAnswer ? <ReactMarkdown>{aiAnswer}</ReactMarkdown> : <div className="text-black/60 dark:text-white/60">AI rationale unavailable.</div>}
          </div>
        ) : null}
      </Card>
      <Card className="h-fit xl:sticky xl:top-20">
        <div className="flex items-center justify-between gap-2">
          <div className="text-sm font-medium">Stock Context</div>
          <div className="text-xs text-black/55 dark:text-white/55">{fmtClock(signals?.current_update?.as_of_et)}</div>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-3">
          <Card className="p-3">
            <div className="text-xs text-black/55 dark:text-white/55">1D Outlook</div>
            <div className="mt-1 text-lg font-semibold">{signals?.forecast?.horizon_1d || analysis.outlook}</div>
          </Card>
          <Card className="p-3">
            <div className="text-xs text-black/55 dark:text-white/55">Prob Up / Down</div>
            <div className="mt-1 text-lg font-semibold">
              {Math.round((signals?.forecast?.prob_up ?? analysis.rise_probability) * 100)}% /{" "}
              {Math.round((signals?.forecast?.prob_down ?? analysis.fall_probability) * 100)}%
            </div>
          </Card>
          <Card className="p-3">
            <div className="text-xs text-black/55 dark:text-white/55">Model</div>
            <div className="mt-1 flex items-center gap-2 text-sm">
              <Badge tone={analysis.model_status.degraded ? "riskMedium" : "bullish"}>
                {analysis.model_status.degraded ? "degraded" : "live"}
              </Badge>
              <span>{analysis.model_status.source}</span>
            </div>
          </Card>
        </div>
      </Card>

      <Card>
        <div className="flex items-center justify-between gap-2">
          <div className="text-sm font-medium">Analyst + News</div>
          <Badge>{news?.degraded ? "degraded" : "live"}</Badge>
        </div>
        <div className="mt-3 rounded-xl border border-black/10 px-3 py-2 text-sm dark:border-white/10">
          <div className="text-xs text-black/55 dark:text-white/55">Analyst Consensus</div>
          {analyst?.available ? (
            <div className="mt-1">
              <span className="font-semibold uppercase">{analyst.consensus}</span>
              <span className="ml-2 text-black/60 dark:text-white/60">
                Buy {analyst.buy} | Hold {analyst.hold} | Sell {analyst.sell}
              </span>
              <div className="mt-1 flex items-center gap-2">
                <Badge tone={analyst.trend === "upgraded" ? "bullish" : analyst.trend === "downgraded" ? "bearish" : "neutral"}>
                  {analyst.trend || "flat"}
                </Badge>
                {analyst.delta ? (
                  <span className="text-xs text-black/55 dark:text-white/55">
                    buy-ratio shift {analyst.delta.buy_ratio_change_pct > 0 ? "+" : ""}
                    {analyst.delta.buy_ratio_change_pct}%
                  </span>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="mt-1 text-black/60 dark:text-white/60">No analyst snapshot on current feed.</div>
          )}
        </div>
        <div className="mt-3 grid gap-2">
          {(news?.headlines || [])
            .slice()
            .sort((a, b) => (b.relevance || 0) - (a.relevance || 0))
            .slice(0, 6)
            .map((h) => (
            <a
              key={`${h.url}-${h.published_at}`}
              href={h.url}
              target="_blank"
              rel="noreferrer"
              className="block rounded-lg border border-black/10 px-3 py-2 text-sm hover:bg-black/[0.03] dark:border-white/10 dark:hover:bg-white/5"
            >
              <div className="line-clamp-2">{h.title}</div>
              <div className="mt-1 flex items-center justify-between text-xs text-black/50 dark:text-white/50">
                <span>
                  {h.source} | {h.published_at.replace("T", " ").replace("Z", " UTC")}
                </span>
                <Badge>{h.relevance ?? 0}</Badge>
              </div>
            </a>
          ))}
        </div>
      </Card>
    </div>
  );
}
