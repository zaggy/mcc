"""Pre-flight budget limit validation for agent LLM calls."""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BudgetLimit, TokenUsage

logger = logging.getLogger(__name__)


@dataclass
class BudgetCheckResult:
    allowed: bool
    warnings: list[str]


def _period_start(period: str) -> datetime:
    """Return the start of the current budget period."""
    now = datetime.now(UTC)
    if period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "weekly":
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    # monthly
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def check_budget(
    db: AsyncSession,
    *,
    agent_id: uuid.UUID,
    agent_type: str,
    project_id: uuid.UUID | None = None,
) -> BudgetCheckResult:
    """Check all applicable budget limits for an agent. Returns whether the call is allowed."""
    # Find all active limits that apply to this agent
    conditions = [BudgetLimit.is_active.is_(True)]
    scope_filter = (
        # Global limits
        (BudgetLimit.scope_type == "global")
        # Project limits
        | ((BudgetLimit.scope_type == "project") & (BudgetLimit.scope_id == project_id))
        # Agent-specific limits
        | ((BudgetLimit.scope_type == "agent") & (BudgetLimit.scope_id == agent_id))
        # Agent-type limits
        | ((BudgetLimit.scope_type == "agent_type") & (BudgetLimit.scope_agent_type == agent_type))
    )
    conditions.append(scope_filter)

    result = await db.execute(select(BudgetLimit).where(*conditions))
    limits = result.scalars().all()

    if not limits:
        return BudgetCheckResult(allowed=True, warnings=[])

    warnings: list[str] = []
    blocked = False

    for limit in limits:
        period_start = _period_start(limit.period)

        # Sum cost for this period within this scope
        usage_query = select(func.coalesce(func.sum(TokenUsage.cost_usd), Decimal("0"))).where(
            TokenUsage.timestamp >= period_start
        )
        if limit.scope_type == "global":
            pass  # no additional filter
        elif limit.scope_type == "project":
            usage_query = usage_query.where(TokenUsage.project_id == limit.scope_id)
        elif limit.scope_type == "agent":
            usage_query = usage_query.where(TokenUsage.agent_id == limit.scope_id)
        elif limit.scope_type == "agent_type":
            usage_query = usage_query.where(TokenUsage.agent_type == limit.scope_agent_type)

        usage_result = await db.execute(usage_query)
        total_cost = usage_result.scalar() or Decimal("0")

        ratio = total_cost / limit.amount_usd if limit.amount_usd > 0 else Decimal("0")

        if ratio >= 1 and limit.action_on_exceed == "block":
            blocked = True
            warnings.append(
                f"Budget limit '{limit.name}' exceeded: "
                f"${total_cost:.4f} / ${limit.amount_usd:.2f} ({limit.period})"
            )
        elif ratio >= limit.alert_threshold:
            warnings.append(
                f"Budget warning '{limit.name}': "
                f"${total_cost:.4f} / ${limit.amount_usd:.2f} ({limit.period}) "
                f"— {ratio * 100:.0f}% used"
            )

    return BudgetCheckResult(allowed=not blocked, warnings=warnings)
