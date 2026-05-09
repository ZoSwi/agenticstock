from __future__ import annotations

from app.integrations.ml_service import MlPrediction

FEATURE_EXPLANATIONS = {
    "sma_50_ratio": "Price trend vs 50-day average is supportive",
    "sma_200_ratio": "Price trend vs 200-day average is supportive",
    "rsi_14": "Momentum (RSI-14) is in a constructive range",
    "macd": "MACD momentum trend is improving",
    "macd_signal": "MACD signal confirms directional momentum",
    "atr_14_pct": "Volatility context (ATR-14) can support stronger directional moves",
    "ret_5d": "Recent 5-day return trend supports continuation",
    "ret_20d": "Recent 20-day return trend supports continuation",
    "vol_20d": "Recent volatility regime supports directional follow-through",
    "volume_z_20": "Volume activity is elevated and supports conviction",
}

FEATURE_RISK_EXPLANATIONS = {
    "sma_50_ratio": "Price is weak relative to the 50-day trend and can face resistance",
    "sma_200_ratio": "Price is weak relative to the 200-day trend, raising downside risk",
    "rsi_14": "Momentum (RSI-14) is stretched and can mean-revert",
    "macd": "MACD momentum trend is weakening",
    "macd_signal": "MACD signal weakens near-term momentum confirmation",
    "atr_14_pct": "High ATR-14 implies wider swings and larger drawdown risk",
    "ret_5d": "Recent 5-day return profile is unstable",
    "ret_20d": "Recent 20-day return profile is weakening",
    "vol_20d": "Elevated volatility regime increases downside tail risk",
    "volume_z_20": "Unusual volume can reflect event risk and instability",
}


def _humanize_feature_reason(raw: str, *, positive: bool) -> str:
    key = (raw or "").strip()
    if not key:
        return raw
    low = key.lower()
    if "(importance)" not in low:
        return raw
    feature = low.replace("(importance)", "").strip()
    if positive:
        return FEATURE_EXPLANATIONS.get(feature, f"Model feature `{feature}` supports upside probability")
    return FEATURE_RISK_EXPLANATIONS.get(feature, f"Model feature `{feature}` raises downside risk")


def suggested_action_from(pred: MlPrediction) -> str:
    outlook = pred.outlook
    risk = pred.risk_level
    conf = pred.confidence_score

    if outlook == "bearish" and (risk == "high" or conf >= 0.6):
        return "avoid"
    if outlook == "bearish":
        return "watchlist"
    if outlook == "neutral" and risk in {"high"}:
        return "wait"
    if outlook == "neutral":
        return "watchlist"
    # bullish
    if risk == "high":
        return "invest gradually"
    if conf < 0.55:
        return "invest gradually"
    return "invest now"


def best_for_from(pred: MlPrediction) -> str:
    if pred.risk_level == "high":
        return "Advanced users comfortable with volatility"
    if pred.risk_level == "medium":
        return "Intermediate users seeking balanced risk"
    return "Beginners and long-term investors seeking lower volatility"


def drivers_from(pred: MlPrediction) -> tuple[list[str], list[str]]:
    growth = []
    fall = []

    for f in pred.top_positive_features[:5]:
        growth.append(_humanize_feature_reason(f, positive=True))
    for f in pred.top_negative_features[:5]:
        fall.append(_humanize_feature_reason(f, positive=False))

    if pred.volatility_detected:
        fall.append("Elevated volatility increases downside risk and drawdowns")

    if not growth:
        growth = [
            "Recent trend and momentum signals lean positive (model-driven)",
            "Risk-adjusted factors support upside probability (model-driven)",
        ]
    if not fall:
        fall = [
            "Macro/sector conditions could outweigh technical strength (scenario risk)",
            "Earnings or guidance surprises can shift direction quickly (event risk)",
        ]

    return growth, fall


def augment_drivers_with_context(
    growth: list[str],
    fall: list[str],
    *,
    fundamentals: dict | None = None,
    news_avg_sentiment: float | None = None,
    news_count: int | None = None,
    macro: dict[str, float] | None = None,
    sector: dict | None = None,
) -> tuple[list[str], list[str]]:
    g = list(growth)
    f = list(fall)

    if fundamentals:
        rev = fundamentals.get("revenue_growth")
        eg = fundamentals.get("earnings_growth")
        pm = fundamentals.get("profit_margins")
        dte = fundamentals.get("debt_to_equity")
        pe = fundamentals.get("pe_ttm")

        if rev is not None and rev > 0.08:
            g.append(f"Revenue growth is positive (~{rev:.0%}) which can support upside if it persists")
        if eg is not None and eg > 0.08:
            g.append(f"Earnings growth is positive (~{eg:.0%}) which can improve sentiment and valuation support")
        if pm is not None and pm < 0.05:
            f.append("Thin profit margins can amplify downside if growth slows or costs rise")
        if dte is not None and dte > 150:
            f.append("Higher leverage (debt-to-equity elevated) can increase downside risk in tighter conditions")
        if pe is not None and pe > 35:
            f.append("Valuation pressure (high P/E) can cap upside if execution disappoints")

    if news_avg_sentiment is not None and news_count is not None:
        if news_count >= 5 and news_avg_sentiment >= 0.15:
            g.append("Recent news sentiment has skewed positive (headline sentiment)")
        if news_count >= 5 and news_avg_sentiment <= -0.15:
            f.append("Recent news sentiment has skewed negative (headline sentiment)")
        if news_count >= 12 and abs(news_avg_sentiment) < 0.05:
            f.append("High news volume with neutral sentiment can signal uncertainty and event-driven chop")

    if macro:
        dff = macro.get("DFF")
        dgs10 = macro.get("DGS10")
        if dff is not None and dff >= 4.5:
            f.append("Higher policy rates can compress risk assets and raise discount-rate pressure")
        if dgs10 is not None and dgs10 >= 4.2:
            f.append("Elevated long rates can pressure high-duration growth stocks and valuations")

    if sector:
        r20 = sector.get("ret_20d")
        v20 = sector.get("vol_20d")
        if r20 is not None and r20 > 0.03:
            g.append("Sector trend has been supportive over the last month (rotation tailwind)")
        if r20 is not None and r20 < -0.03:
            f.append("Sector trend has been weak over the last month (rotation headwind)")
        if v20 is not None and v20 > 0.35:
            f.append("Sector volatility is elevated, increasing whipsaw and drawdown risk")

    # keep tidy
    g = g[:8]
    f = f[:8]
    return g, f


def augment_drivers_with_snapshot(
    growth: list[str],
    fall: list[str],
    *,
    ticker: str,
    technical: dict | None = None,
    headlines: list[dict] | None = None,
) -> tuple[list[str], list[str]]:
    g = list(growth)
    f = list(fall)
    g_snap: list[str] = []
    f_snap: list[str] = []
    symbol = (ticker or "").upper().strip()

    if technical:
        close = technical.get("close")
        sma50 = technical.get("sma50")
        sma50_pct = technical.get("sma50_pct")
        macd = technical.get("macd")
        macd_signal = technical.get("macd_signal")
        atr14_pct = technical.get("atr14_pct")
        if close is not None and sma50 is not None and sma50_pct is not None:
            rel = "above" if sma50_pct >= 0 else "below"
            text = f"{symbol} is {abs(sma50_pct):.2f}% {rel} its 50-day average (close {close:.2f} vs SMA50 {sma50:.2f})"
            (g_snap if sma50_pct >= 0 else f_snap).append(text)
        if macd is not None and macd_signal is not None:
            spread = macd - macd_signal
            text = f"MACD spread for {symbol} is {spread:+.4f} (MACD {macd:+.4f} vs signal {macd_signal:+.4f})"
            (g_snap if spread >= 0 else f_snap).append(text)
        if atr14_pct is not None:
            if atr14_pct >= 4.0:
                f_snap.append(f"{symbol} ATR-14 is elevated at {atr14_pct:.2f}% of price, implying wider downside swings")
            elif atr14_pct >= 2.0:
                f_snap.append(f"{symbol} ATR-14 is moderate at {atr14_pct:.2f}% of price; expect larger than average ranges")
            else:
                g_snap.append(f"{symbol} ATR-14 is contained at {atr14_pct:.2f}% of price, supporting cleaner trend behavior")

    if headlines:
        source_counts: dict[str, int] = {}
        pos = 0
        neg = 0
        for h in headlines[:10]:
            source = str(h.get("source") or "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
            title = str(h.get("title") or "").upper()
            if any(k in title for k in ("UPGRADE", "BEAT", "RAISES", "GROWTH", "SURGE", "STRONG")):
                pos += 1
            if any(k in title for k in ("DOWNGRADE", "MISS", "CUTS", "LAWSUIT", "PROBE", "WEAK", "DROP")):
                neg += 1
        if source_counts:
            top_sources = ", ".join([f"{k} ({v})" for k, v in sorted(source_counts.items(), key=lambda i: i[1], reverse=True)[:3]])
            g_snap.append(f"Recent {symbol} headline coverage is active across {top_sources}")
        if pos > neg and pos >= 2:
            g_snap.append(f"Headline tone for {symbol} is net-positive in the latest news cycle ({pos} positive vs {neg} negative flags)")
        elif neg > pos and neg >= 2:
            f_snap.append(f"Headline tone for {symbol} is net-negative in the latest news cycle ({neg} negative vs {pos} positive flags)")
        top = headlines[0]
        top_title = str(top.get("title") or "").strip()
        top_source = str(top.get("source") or "").strip()
        if top_title and top_source:
            f_snap.append(f"Latest catalyst to monitor: {top_source} headline on {symbol} - {top_title[:120]}")
    # Surface ticker-specific snapshot items first so compact UIs (top-4) stay differentiated per stock.
    g_ordered = g_snap + g
    f_ordered = f_snap + f

    def _dedupe(items: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out

    return _dedupe(g_ordered)[:8], _dedupe(f_ordered)[:8]


def watch_next_from(pred: MlPrediction) -> list[str]:
    items: list[str] = []
    if pred.volatility_detected:
        items.append("Volatility regime changes (ATR/realized volatility)")
    items.extend(
        [
            "Next earnings date and guidance",
            "Major support/resistance breaks and volume confirmation",
            "Sector rotation and macro rate expectations",
        ]
    )
    return items[:5]


def watch_next_contextual(
    pred: MlPrediction,
    *,
    ticker: str,
    quote_available: bool,
    news_count: int | None = None,
    news_avg_sentiment: float | None = None,
    fundamentals: dict | None = None,
) -> list[str]:
    out: list[str] = []
    if not quote_available:
        out.append(f"Track {ticker} live quote confirmation before acting on directional outlook.")
    if pred.volatility_detected:
        out.append(f"Watch intraday volatility regime changes for {ticker} before position sizing.")
    if news_count is not None and news_count >= 5:
        if news_avg_sentiment is not None and news_avg_sentiment >= 0.15:
            out.append(f"News flow is positive for {ticker}; monitor if sentiment stays supportive.")
        elif news_avg_sentiment is not None and news_avg_sentiment <= -0.15:
            out.append(f"Negative headline sentiment on {ticker}; monitor for further revisions and guidance risk.")
        else:
            out.append(f"Headline flow is mixed for {ticker}; wait for clearer directional catalysts.")
    if fundamentals:
        pe = fundamentals.get("pe_ttm")
        dte = fundamentals.get("debt_to_equity")
        if pe is not None and pe > 35:
            out.append(f"Valuation watch: {ticker} P/E is elevated; monitor multiple-compression risk.")
        if dte is not None and dte > 150:
            out.append(f"Balance-sheet watch: leverage on {ticker} is elevated; monitor refinancing/rate sensitivity.")

    # Deterministic base items with ticker specificity.
    out.extend(
        [
            f"Next {ticker} earnings date and guidance revisions",
            f"{ticker} key support/resistance breaks with volume confirmation",
            "Sector rotation and macro rate expectations",
        ]
    )

    # Deduplicate while preserving order.
    dedup: list[str] = []
    seen: set[str] = set()
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        dedup.append(item)
    return dedup[:6]
