export type StockAnalysis = {
  ticker: string;
  outlook: "bullish" | "neutral" | "bearish";
  rise_probability: number;
  fall_probability: number;
  confidence_score: number;
  risk_level: "low" | "medium" | "high";
  volatility_detected: boolean;
  time_horizon: { short_term: string; medium_term: string; long_term: string };
  growth_drivers: string[];
  fall_drivers: string[];
  suggested_action: string;
  best_for: string;
  watch_next: string[];
  model_status: {
    source: string;
    degraded: boolean;
    reason?: string | null;
  };
};

export type StockSignals = {
  ticker: string;
  current_update: {
    as_of_et?: string | null;
    market_status?: string | null;
    quote?: {
      ticker: string;
      last: number;
      change: number;
      change_pct: number;
      volume: number;
    } | null;
  };
  nowcast: {
    regime: "risk_on" | "risk_off" | "balanced";
    risk_level: "low" | "medium" | "high";
    volatility_detected: boolean;
    confidence_score: number;
  };
  forecast: {
    horizon_1d: "bullish" | "neutral" | "bearish";
    horizon_5d: string;
    horizon_20d: string;
    prob_up: number;
    prob_down: number;
  };
  degraded: boolean;
  degraded_reason?: string | null;
};

export type StockPricePoint = {
  day: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type PriceSeriesQuery = {
  days?: number;
  mode?: "daily" | "intraday";
  session?: "1D" | "5D";
  resolution?: "1" | "5";
};

export type StockPriceSeries = {
  ticker: string;
  points: StockPricePoint[];
  stats: {
    series_high: number | null;
    series_low: number | null;
    latest_close: number | null;
    daily_change: number | null;
    daily_change_pct: number | null;
  };
  live_quote?: {
    ticker: string;
    last: number;
    change: number;
    change_pct: number;
    volume: number;
  } | null;
};

export type StockQuoteDetail = {
  ticker: string;
  available: boolean;
  last: number | null;
  change: number | null;
  change_pct: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  prev_close: number | null;
  week_52_high: number | null;
  week_52_low: number | null;
  timestamp: number | null;
};

export type MarketPulseRow = {
  ticker: string;
  last: number;
  change: number;
  change_pct: number;
  volume: number;
};

export type MarketPulseIndex = {
  name: string;
  symbol: string;
  last: number;
  change: number;
  change_pct: number;
};

export type MarketPulse = {
  as_of_utc: string;
  as_of_et: string;
  market_status: "open" | "closed";
  data_source?: string;
  universe_size: number;
  market_breadth?: {
    advancers: number;
    decliners: number;
    unchanged: number;
  };
  provider_status?: {
    finnhub: boolean;
    alphavantage: boolean;
    stooq?: boolean;
    yahoo: boolean;
  };
  provider_diagnostics?: Record<
    string,
    {
      configured: boolean;
      ok: boolean;
      rows: number;
      latency_ms: number | null;
      score: number;
      error?: string | null;
    }
  >;
  degraded_reason?: string | null;
  indices: MarketPulseIndex[];
  sector_leaders?: MarketPulseIndex[];
  stale?: boolean;
  top_gainers: MarketPulseRow[];
  top_losers: MarketPulseRow[];
  most_active: MarketPulseRow[];
};

export type LiveNewsHeadline = {
  source: string;
  title: string;
  url: string;
  published_at: string;
  relevance?: number;
};

export type LiveNewsResponse = {
  as_of_utc: string;
  source: string;
  count: number;
  degraded: boolean;
  headlines: LiveNewsHeadline[];
};

export type AnalystView = {
  ticker: string;
  available: boolean;
  source: string;
  consensus: "buy" | "hold" | "sell" | null;
  buy: number;
  hold: number;
  sell: number;
  as_of: string | null;
  trend?: "upgraded" | "downgraded" | "flat";
  delta?: {
    buy_change: number;
    hold_change: number;
    sell_change: number;
    buy_ratio_change_pct: number;
  } | null;
};

export type StockAiOutcome = {
  ticker: string;
  provider: string;
  degraded: boolean;
  answer_markdown: string;
  decision: {
    bias: "bullish" | "neutral" | "bearish";
    action: string;
    confidence_score: number;
    risk_level: "low" | "medium" | "high";
    expected_return_20d: number;
    horizon_alignment_ok: boolean;
    note: string;
  };
  trade_plan: {
    entry_style: string;
    stop_loss_pct: number;
    target_pct: number;
    risk_reward_ratio: number;
    max_loss_per_position_pct_of_capital: number;
  };
  scenarios_20d: Array<{
    name: "bull" | "base" | "bear";
    probability: number;
    return_pct: number;
  }>;
  consistency: {
    overall_outlook: "bullish" | "neutral" | "bearish";
    short_term: string;
    medium_term: string;
    long_term: string;
    aligned: boolean;
  };
};

export type StockRiskEngine = {
  ticker: string;
  inputs: {
    capital: number;
    risk_budget_pct: number;
  };
  market: {
    entry_price: number | null;
    quote_source: string;
  };
  risk_plan: {
    risk_level: "low" | "medium" | "high";
    stop_loss_pct: number;
    target_pct: number;
    reward_risk_ratio: number;
    risk_budget_amount: number;
    position_shares: number | null;
    max_notional: number | null;
  };
  model_context: {
    outlook: "bullish" | "neutral" | "bearish";
    confidence_score: number;
    rise_probability: number;
    fall_probability: number;
  };
};

export type PortfolioPosition = {
  ticker: string;
  quantity: number;
  avg_cost: number;
};

export type PortfolioSummaryItem = {
  ticker: string;
  quantity: number;
  avg_cost: number;
  last_price: number | null;
  cost_basis: number;
  market_value: number | null;
  unrealized_pl: number | null;
  unrealized_pl_pct: number | null;
};

export type PortfolioSummary = {
  user_id: string;
  positions: PortfolioSummaryItem[];
  totals: {
    cost_basis: number;
    market_value: number;
    unrealized_pl: number;
    unrealized_pl_pct: number;
  };
};

export type AuditEvent = {
  id: number;
  ticker: string;
  decision: string;
  confidence_score: number;
  risk_level: "low" | "medium" | "high";
  source: string;
  created_at: string | null;
};

function getApiBase() {
  // Browser should call the host-exposed backend URL.
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  }
  // Server-side code inside Docker should call backend service directly.
  return process.env.INTERNAL_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://backend:8000";
}

type ApiOptions = {
  timeoutMs?: number;
  signal?: AbortSignal;
};

async function api<T>(path: string, init?: RequestInit, opts?: ApiOptions): Promise<T> {
  const timeoutMs = Math.max(1000, opts?.timeoutMs ?? 15000);
  const ctrl = new AbortController();
  const onAbort = () => ctrl.abort();
  if (opts?.signal) {
    if (opts.signal.aborted) ctrl.abort();
    else opts.signal.addEventListener("abort", onAbort, { once: true });
  }
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    let lastErr: unknown;
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        const res = await fetch(`${getApiBase()}${path}`, {
          ...init,
          signal: ctrl.signal,
          headers: {
            "content-type": "application/json",
            ...(init?.headers || {}),
          },
          cache: "no-store",
        });
        if (!res.ok) {
          const text = await res.text();
          throw new Error(text || `Request failed: ${res.status}`);
        }
        return (await res.json()) as T;
      } catch (e: any) {
        lastErr = e;
        if (ctrl.signal.aborted) throw new Error("Request timed out");
        // Retry once for transient network failures like ERR_CONNECTION_RESET.
        if (attempt === 0 && (e?.name === "TypeError" || /Failed to fetch/i.test(String(e?.message || "")))) {
          await new Promise((r) => setTimeout(r, 250));
          continue;
        }
        throw e;
      }
    }
    throw lastErr ?? new Error("Request failed");
  } finally {
    clearTimeout(timer);
    if (opts?.signal) opts.signal.removeEventListener("abort", onAbort);
  }
}

export async function fetchAnalysis(ticker: string) {
  return api<StockAnalysis>(`/stocks/${encodeURIComponent(ticker)}/analysis`);
}

export async function fetchSignals(ticker: string) {
  return api<StockSignals>(`/stocks/${encodeURIComponent(ticker)}/signals`);
}

export async function fetchPriceSeries(ticker: string, query: PriceSeriesQuery = {}) {
  const mode = query.mode === "intraday" ? "intraday" : "daily";
  const params = new URLSearchParams();
  params.set("mode", mode);
  if (mode === "intraday") {
    params.set("session", query.session === "5D" ? "5D" : "1D");
    params.set("resolution", query.resolution === "1" ? "1" : "5");
  } else {
    params.set("days", String(Math.max(10, Math.min(365, query.days ?? 60))));
  }
  return api<StockPriceSeries>(`/stocks/${encodeURIComponent(ticker)}/price-series?${params.toString()}`);
}

export async function fetchQuoteDetail(ticker: string) {
  return api<StockQuoteDetail>(`/stocks/${encodeURIComponent(ticker)}/quote-detail`);
}

export async function searchStocks(q: string, signal?: AbortSignal) {
  return api<{ results: Array<{ ticker: string; name?: string | null }> }>(
    `/stocks/search?q=${encodeURIComponent(q)}`,
    undefined,
    { timeoutMs: 6000, signal }
  );
}

export async function aiQuery(payload: { query: string; user_type: string; user_id?: string }) {
  return api<{ answer_markdown: string; structured: any }>(`/ai/query`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getWatchlist(userId: string) {
  return api<{ user_id: string; tickers: string[] }>(`/watchlist?user_id=${encodeURIComponent(userId)}`);
}

export async function addToWatchlist(userId: string, ticker: string) {
  return api(`/watchlist`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, ticker }),
  });
}

export async function fetchMarketPulse(limit: number = 8, forceRefresh: boolean = false) {
  const l = Math.max(3, Math.min(30, limit));
  return api<MarketPulse>(`/stocks/market/live?limit=${l}${forceRefresh ? "&force_refresh=true" : ""}`);
}

export async function fetchLiveNews(limit: number = 20) {
  return api<LiveNewsResponse>(`/news/live?limit=${Math.max(5, Math.min(60, limit))}`);
}

export async function fetchTickerNews(ticker: string, limit: number = 20) {
  return api<LiveNewsResponse & { ticker: string }>(
    `/news/${encodeURIComponent(ticker)}?limit=${Math.max(5, Math.min(60, limit))}`
  );
}

export async function fetchAnalystView(ticker: string) {
  return api<AnalystView>(`/stocks/${encodeURIComponent(ticker)}/analyst-view`);
}

export async function fetchStockAiOutcome(
  ticker: string,
  userType: "beginner" | "intermediate" | "advanced" = "advanced"
) {
  return api<StockAiOutcome>(
    `/stocks/${encodeURIComponent(ticker)}/ai-outcome?user_type=${encodeURIComponent(userType)}`
  );
}

export async function fetchStockRiskEngine(
  ticker: string,
  capital: number = 100000,
  riskBudgetPct: number = 0.01
) {
  return api<StockRiskEngine>(
    `/stocks/${encodeURIComponent(ticker)}/risk-engine?capital=${encodeURIComponent(String(capital))}&risk_budget_pct=${encodeURIComponent(String(riskBudgetPct))}`
  );
}

export async function upsertPortfolioPosition(payload: {
  user_id: string;
  ticker: string;
  quantity: number;
  avg_cost: number;
}) {
  return api<{ ok: boolean; ticker: string }>(`/portfolio/positions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchPortfolioPositions(userId: string) {
  return api<{ user_id: string; positions: PortfolioPosition[] }>(
    `/portfolio/positions?user_id=${encodeURIComponent(userId)}`
  );
}

export async function deletePortfolioPosition(userId: string, ticker: string) {
  return api<{ ok: boolean }>(
    `/portfolio/positions?user_id=${encodeURIComponent(userId)}&ticker=${encodeURIComponent(ticker)}`,
    { method: "DELETE" }
  );
}

export async function fetchPortfolioSummary(userId: string) {
  return api<PortfolioSummary>(`/portfolio/summary?user_id=${encodeURIComponent(userId)}`);
}

export async function createAuditEvent(payload: {
  user_id: string;
  ticker: string;
  decision: string;
  confidence_score: number;
  risk_level: "low" | "medium" | "high";
  source?: string;
}) {
  return api<{ ok: boolean; id: number }>(`/audit/events`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchAuditEvents(userId: string, limit: number = 50) {
  return api<{ user_id: string; events: AuditEvent[] }>(
    `/audit/events?user_id=${encodeURIComponent(userId)}&limit=${Math.max(1, Math.min(500, limit))}`
  );
}

export function getMarketStreamUrl(limit: number = 10, intervalSeconds: number = 12) {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const l = Math.max(3, Math.min(30, limit));
  const i = Math.max(5, Math.min(60, intervalSeconds));
  return `${base}/stocks/market/stream?limit=${l}&interval_seconds=${i}`;
}
