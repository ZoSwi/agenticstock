from __future__ import annotations

from app.schemas.analysis import StockAnalysisResponse


def _tone(user_type: str) -> dict[str, str]:
    if user_type == "advanced":
        return {
            "headline": "Model-driven directional outlook",
            "style": "technical",
        }
    if user_type == "intermediate":
        return {
            "headline": "Risk-aware directional outlook",
            "style": "balanced",
        }
    return {
        "headline": "Simple directional outlook",
        "style": "simple",
    }


def render_analysis_markdown(a: StockAnalysisResponse, user_type: str) -> str:
    t = _tone(user_type)
    lines: list[str] = []
    action_label = a.suggested_action.replace("_", " ").title()
    decision = "Wait"
    if a.suggested_action in {"invest now", "invest gradually"}:
        decision = "Invest"
    elif a.suggested_action in {"avoid"}:
        decision = "Avoid"

    lines.append(f"## {a.ticker} - {t['headline']}")
    lines.append("")
    lines.append(f"**Decision**: `{decision}`")
    lines.append(f"**Suggested action**: `{action_label}`")
    lines.append(f"**Outlook**: `{a.outlook}` | **Confidence**: `{a.confidence_score:.0%}` | **Risk**: `{a.risk_level}`")
    lines.append(f"**Prob Up / Down**: `{a.rise_probability:.0%}` / `{a.fall_probability:.0%}`")
    lines.append(f"**Volatility**: `{'high' if a.volatility_detected else 'normal'}`")
    lines.append("")
    lines.append("### Time Horizon")
    lines.append(f"- **Short-term**: `{a.time_horizon.short_term}`")
    lines.append(f"- **Medium-term**: `{a.time_horizon.medium_term}`")
    lines.append(f"- **Long-term**: `{a.time_horizon.long_term}`")
    lines.append("")

    lines.append("### Top Growth Drivers")
    for d in a.growth_drivers[:4]:
        lines.append(f"- {d}")
    lines.append("")

    lines.append("### Top Risk Drivers")
    for d in a.fall_drivers[:4]:
        lines.append(f"- {d}")
    lines.append("")

    lines.append("### What To Watch Next")
    for w in a.watch_next[:4]:
        lines.append(f"- {w}")
    lines.append("")

    if user_type == "beginner":
        lines.append("### Beginner Playbook")
        if a.suggested_action in {"invest now", "invest gradually"}:
            lines.append("- Consider sizing small first; add only if the thesis stays intact.")
            lines.append("- Avoid making decisions right before earnings unless you accept event risk.")
        elif a.suggested_action in {"wait", "watchlist"}:
            lines.append("- Add to your watchlist and set alerts for earnings and major price moves.")
        else:
            lines.append("- Focus on stronger, lower-risk setups; revisit if conditions improve.")

    if user_type == "advanced":
        lines.append("### Advanced Notes")
        lines.append("- Treat probabilities as calibration targets, not certainties; consider a rules-based entry/exit plan.")
        lines.append("- Manage tail risk around earnings/macro catalysts; consider hedging if exposure is large.")

    lines.append("")
    lines.append("_Not personalized financial advice._")

    return "\n".join(lines).strip() + "\n"
