"""Async HTTP client for OpenRouter chat completions with retry/backoff."""

import asyncio
import logging
import time
from decimal import Decimal

import httpx

from app.core.config import settings
from app.models.openrouter import OpenRouterResponse, OpenRouterUsage

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Wraps httpx.AsyncClient for OpenRouter API calls."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.OPENROUTER_BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> OpenRouterResponse:
        """Send a chat completion request with retry/backoff on failure."""
        model = model or settings.OPENROUTER_DEFAULT_MODEL
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        last_error: Exception | None = None
        for attempt in range(settings.OPENROUTER_MAX_RETRIES):
            start = time.monotonic()
            try:
                resp = await self._client.post("/chat/completions", json=payload)

                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", 2**attempt))
                    logger.warning("Rate limited, retrying after %.1fs", retry_after)
                    await asyncio.sleep(retry_after)
                    continue

                resp.raise_for_status()
                duration_ms = int((time.monotonic() - start) * 1000)
                data = resp.json()

                choice = data["choices"][0]
                content = choice["message"]["content"]
                raw_usage = data.get("usage", {})
                usage = OpenRouterUsage(
                    prompt_tokens=raw_usage.get("prompt_tokens", 0),
                    completion_tokens=raw_usage.get("completion_tokens", 0),
                    total_tokens=raw_usage.get("total_tokens", 0),
                )

                cost_usd = Decimal("0")
                if "usage" in data and "total_cost" in data["usage"]:
                    cost_usd = Decimal(str(data["usage"]["total_cost"]))

                return OpenRouterResponse(
                    content=content,
                    model=data.get("model", model),
                    usage=usage,
                    cost_usd=cost_usd,
                    duration_ms=duration_ms,
                )

            except httpx.HTTPStatusError as exc:
                last_error = exc
                logger.warning(
                    "OpenRouter HTTP %s on attempt %d/%d",
                    exc.response.status_code,
                    attempt + 1,
                    settings.OPENROUTER_MAX_RETRIES,
                )
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning(
                    "OpenRouter request error on attempt %d/%d: %s",
                    attempt + 1,
                    settings.OPENROUTER_MAX_RETRIES,
                    exc,
                )

            if attempt < settings.OPENROUTER_MAX_RETRIES - 1:
                backoff = 2**attempt
                await asyncio.sleep(backoff)

        raise RuntimeError(
            f"OpenRouter request failed after {settings.OPENROUTER_MAX_RETRIES} attempts"
        ) from last_error
