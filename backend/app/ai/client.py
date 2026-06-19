"""OpenRouter chat client (HTTPX).

Calls OpenRouter directly (CLAUDE.md: OpenRouter is the LLM path; InsForge is not in
it). The API key comes from settings/env and is never logged. Errors are surfaced as
typed exceptions so the stream can degrade gracefully instead of crashing.
"""

from __future__ import annotations

import asyncio

import httpx
from loguru import logger

from app.core.config import settings


class LLMError(Exception):
    """LLM call failed (transport, HTTP status, or empty/blocked response)."""


class LLMParseError(LLMError):
    """The model replied but the content was not valid Diagnosis JSON."""


# Status codes worth retrying (rate limit + transient server errors).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


async def chat(messages: list[dict], *, max_retries: int = 2) -> str:
    """Send a chat completion request and return the assistant's message content.

    Retries transport errors and retryable status codes with simple backoff. Raises
    :class:`LLMError` on exhaustion or a non-retryable failure.
    """
    if not settings.openrouter_api_key:
        raise LLMError("OPENROUTER_API_KEY is not set")
    if not settings.openrouter_model:
        raise LLMError("OPENROUTER_MODEL is not set")

    url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        # Optional OpenRouter attribution headers (not secret).
        "HTTP-Referer": "https://github.com/Devblaise/AI-DevOps-K8s-Agent",
        "X-Title": "AI Kubernetes Agent",
    }
    payload = {
        "model": settings.openrouter_model,
        "messages": messages,
        "temperature": settings.llm_temperature,
    }

    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as http:
        for attempt in range(1, max_retries + 2):  # initial try + max_retries
            try:
                resp = await http.post(url, headers=headers, json=payload)
                if resp.status_code in _RETRYABLE_STATUS:
                    raise LLMError(f"OpenRouter returned {resp.status_code}")
                resp.raise_for_status()
                data = resp.json()
                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content")
                )
                if not content:
                    raise LLMError("OpenRouter returned an empty response")
                return content
            except (httpx.HTTPStatusError, httpx.TransportError, LLMError) as exc:
                last_exc = exc
                # Don't retry clear client errors (e.g. bad model id / auth).
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status is not None and status not in _RETRYABLE_STATUS:
                    raise LLMError(f"OpenRouter request failed: {_safe(exc)}") from exc
                if attempt <= max_retries:
                    backoff = 0.5 * attempt
                    logger.warning(
                        "LLM call attempt {} failed ({}); retrying in {}s",
                        attempt,
                        _safe(exc),
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue
                raise LLMError(f"OpenRouter request failed: {_safe(exc)}") from exc

    # Unreachable, but keeps type checkers happy.
    raise LLMError(f"OpenRouter request failed: {_safe(last_exc)}")


def _safe(exc: Exception | None) -> str:
    """Short error description that cannot leak the API key."""
    return type(exc).__name__ if exc is None else f"{type(exc).__name__}: {exc}"
