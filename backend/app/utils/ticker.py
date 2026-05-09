import re


_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")


def extract_tickers(text: str) -> list[str]:
    candidates = _TICKER_RE.findall(text.upper())
    # Filter common non-ticker words that show up in queries.
    stop = {
        "A",
        "AI",
        "AND",
        "ARE",
        "BUY",
        "CAN",
        "DO",
        "FOR",
        "I",
        "IN",
        "IS",
        "IT",
        "MY",
        "NOW",
        "OF",
        "OR",
        "SHOULD",
        "STOCK",
        "THE",
        "TO",
        "VS",
        "WHAT",
        "WHEN",
        "WHY",
        "YOU",
    }
    tickers = []
    for c in candidates:
        if c in stop:
            continue
        if c not in tickers:
            tickers.append(c)
    return tickers

