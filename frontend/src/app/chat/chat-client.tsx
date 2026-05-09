"use client";

import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import * as React from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { aiQuery } from "@/lib/api";

export function ChatClient() {
  const sp = useSearchParams();
  const seed = sp.get("q") || "";

  const [query, setQuery] = React.useState(seed || "Should I invest in TSLA?");
  const [userType, setUserType] = React.useState<"beginner" | "intermediate" | "advanced">("beginner");
  const [loading, setLoading] = React.useState(false);
  const [answer, setAnswer] = React.useState<string>("");
  const [structured, setStructured] = React.useState<any>(null);
  const [error, setError] = React.useState<string | null>(null);

  const ask = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await aiQuery({ query, user_type: userType, user_id: "demo" });
      setAnswer(res.answer_markdown);
      setStructured(res.structured);
    } catch (e: any) {
      setError(e?.message || "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">AI Chat</h2>
          <p className="mt-1 text-sm text-black/60 dark:text-white/60">
            Ask "what should I do?" questions and get probabilistic guidance with risks.
          </p>
        </div>
        <Badge>Explanation adapts to you</Badge>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <div className="text-sm font-medium">Ask</div>
          <div className="mt-3 space-y-3">
            <Input value={query} onChange={(e) => setQuery(e.target.value)} />
            <div className="flex flex-wrap gap-2">
              {(["beginner", "intermediate", "advanced"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setUserType(t)}
                  className={
                    userType === t
                      ? "rounded-full bg-black px-3 py-1 text-xs font-medium text-white dark:bg-white dark:text-black"
                      : "rounded-full border border-black/10 bg-white/60 px-3 py-1 text-xs text-black/70 hover:bg-white dark:border-white/10 dark:bg-white/5 dark:text-white/70 dark:hover:bg-white/10"
                  }
                >
                  {t}
                </button>
              ))}
            </div>
            <Button onClick={ask} disabled={loading || !query.trim()}>
              {loading ? "Thinking..." : "Ask the agent"}
            </Button>
            {error ? <div className="text-sm text-rose-600">{error}</div> : null}
            <div className="text-xs text-black/50 dark:text-white/50">
              Tip: try "Compare AAPL vs MSFT" or "What should I do with NVDA now?"
            </div>
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <div className="text-sm font-medium">Answer</div>
          {structured && !structured.mode ? (
            <div className="mt-3 grid gap-2 md:grid-cols-5">
              <Card className="p-2.5">
                <div className="text-[11px] text-black/55 dark:text-white/55">Decision</div>
                <div className="text-sm font-semibold">{String(structured.suggested_action || "-").replace("_", " ")}</div>
              </Card>
              <Card className="p-2.5">
                <div className="text-[11px] text-black/55 dark:text-white/55">Outlook</div>
                <div className="text-sm font-semibold">{structured.outlook || "-"}</div>
              </Card>
              <Card className="p-2.5">
                <div className="text-[11px] text-black/55 dark:text-white/55">Confidence</div>
                <div className="text-sm font-semibold">{structured.confidence_score != null ? `${Math.round(structured.confidence_score * 100)}%` : "-"}</div>
              </Card>
              <Card className="p-2.5">
                <div className="text-[11px] text-black/55 dark:text-white/55">Risk</div>
                <div className="text-sm font-semibold">{structured.risk_level || "-"}</div>
              </Card>
              <Card className="p-2.5">
                <div className="text-[11px] text-black/55 dark:text-white/55">Prob Up / Down</div>
                <div className="text-sm font-semibold">
                  {structured.rise_probability != null && structured.fall_probability != null
                    ? `${Math.round(structured.rise_probability * 100)}% / ${Math.round(structured.fall_probability * 100)}%`
                    : "-"}
                </div>
              </Card>
            </div>
          ) : null}
          <div className="prose mt-4 max-w-none text-sm leading-6 prose-headings:mb-2 prose-headings:mt-4 prose-p:my-2 prose-li:my-0.5 dark:prose-invert">
            {answer ? <ReactMarkdown>{answer}</ReactMarkdown> : <div className="text-black/60 dark:text-white/60">Ask a ticker question to get a decision-first answer.</div>}
          </div>
        </Card>
      </div>
    </>
  );
}
