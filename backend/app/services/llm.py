from __future__ import annotations

import json
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.core.config import settings


SYSTEM_PROMPT = """You are a financial education assistant inside an app that outputs probabilistic stock direction outlooks.
Rules (must follow):
- Do NOT predict exact future prices or price targets.
- Do NOT guarantee investment outcomes.
- Keep the user's risk in mind; be clear this is not personalized financial advice.
- Preserve the factual structured data implied by the user message; you may rephrase for clarity.
- Output valid Markdown only (headings, bullets). No JSON unless asked.
"""


def resolve_llm_provider() -> str:
    provider = (settings.llm_provider or "none").lower().strip()
    if provider != "auto":
        return provider
    if settings.openai_api_key:
        return "openai"
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.ollama_base_url and settings.ollama_model:
        return "ollama"
    return "none"


async def enhance_answer_markdown(
    *,
    draft_markdown: str,
    structured: dict[str, Any],
    user_type: str,
) -> str:
    """Optional LLM polish. On any failure, caller should use draft_markdown."""
    provider = resolve_llm_provider()
    user_block = f"User level: {user_type}\n\nStructured JSON (source of truth for numbers):\n{json.dumps(structured, indent=2)[:12000]}\n\nDraft Markdown:\n{draft_markdown}"

    try:
        if provider == "openai":
            if not settings.openai_api_key:
                return draft_markdown
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": user_block
                        + "\n\nRewrite the Draft into clearer Markdown. Keep the same numbers and outlook labels.",
                    },
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            text = resp.choices[0].message.content or ""
            return text.strip() or draft_markdown

        if provider == "anthropic":
            if not settings.anthropic_api_key:
                return draft_markdown
            async with httpx.AsyncClient(timeout=60.0) as http:
                r = await http.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": settings.anthropic_model,
                        "max_tokens": 2048,
                        "system": SYSTEM_PROMPT,
                        "messages": [{"role": "user", "content": user_block}],
                    },
                )
                r.raise_for_status()
                data = r.json()
                parts = data.get("content") or []
                text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
                return text.strip() or draft_markdown

        if provider == "ollama":
            base = settings.ollama_base_url.rstrip("/")
            url = f"{base}/v1/chat/completions"
            async with httpx.AsyncClient(timeout=120.0) as http:
                r = await http.post(
                    url,
                    json={
                        "model": settings.ollama_model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_block},
                        ],
                        "temperature": 0.3,
                    },
                )
                if r.status_code >= 400:
                    return draft_markdown
                data = r.json()
                text = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
                return text.strip() or draft_markdown
    except Exception:
        return draft_markdown

    return draft_markdown
