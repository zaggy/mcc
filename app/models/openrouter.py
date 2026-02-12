"""Pydantic schemas for OpenRouter API interactions."""

from decimal import Decimal

from pydantic import BaseModel


class OpenRouterUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenRouterResponse(BaseModel):
    content: str
    model: str
    usage: OpenRouterUsage
    cost_usd: Decimal = Decimal("0")
    duration_ms: int = 0
