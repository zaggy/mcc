"""Abstract base agent with the core execution loop."""

import logging
import uuid
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context import count_messages_tokens, truncate_messages
from app.db.models import Agent, Conversation, Message
from app.models.openrouter import OpenRouterResponse
from app.services.budget_service import check_budget
from app.services.openrouter import OpenRouterClient
from app.services.token_tracker import record_usage

logger = logging.getLogger(__name__)

# Default context window budget (tokens). Conservative to work across models.
DEFAULT_MAX_CONTEXT_TOKENS = 100_000


class BaseAgent(ABC):
    """Abstract base for all MCC agents."""

    def __init__(
        self,
        agent_record: Agent,
        openrouter: OpenRouterClient,
    ) -> None:
        self.agent_record = agent_record
        self.openrouter = openrouter

    @property
    def agent_id(self) -> uuid.UUID:
        return self.agent_record.id

    @property
    def agent_type(self) -> str:
        return self.agent_record.type

    @property
    def project_id(self) -> uuid.UUID | None:
        return self.agent_record.project_id

    @abstractmethod
    def default_system_prompt(self) -> str:
        """Return the role-specific system prompt for this agent type."""
        ...

    @abstractmethod
    def allowed_recipients(self) -> list[str]:
        """Return agent types this agent is allowed to message."""
        ...

    def _get_system_prompt(self) -> str:
        """Use custom system prompt if set on agent record, else the default."""
        return self.agent_record.system_prompt or self.default_system_prompt()

    def _get_model(self) -> str | None:
        """Extract model from agent's config, or None to use default."""
        config = self.agent_record.model_config_json or {}
        return config.get("model")

    def _get_temperature(self) -> float:
        config = self.agent_record.model_config_json or {}
        return float(config.get("temperature", 0.7))

    def _get_max_context_tokens(self) -> int:
        config = self.agent_record.model_config_json or {}
        return int(config.get("max_context_tokens", DEFAULT_MAX_CONTEXT_TOKENS))

    async def process_message(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> Message | None:
        """Core execution loop: budget check → build context → call LLM → save response."""
        # 1. Budget pre-flight
        budget_result = await check_budget(
            db,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            project_id=self.project_id,
        )
        for warning in budget_result.warnings:
            logger.warning("Budget: %s", warning)

        if not budget_result.allowed:
            logger.error("Budget exceeded for agent %s, blocking LLM call", self.agent_id)
            return None

        # 2. Load conversation history
        conv = await db.get(Conversation, conversation_id)
        if not conv:
            logger.error("Conversation %s not found", conversation_id)
            return None

        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        history = result.scalars().all()

        # 3. Build messages array
        system_prompt = self._get_system_prompt()
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        for msg in history:
            is_self = msg.author_type == "agent" and msg.agent_id == self.agent_id
            role = "assistant" if is_self else "user"
            messages.append({"role": role, "content": msg.content})

        # 4. Context window management
        max_tokens = self._get_max_context_tokens()
        if count_messages_tokens(messages) > max_tokens:
            messages = truncate_messages(messages, max_tokens)

        # 5. Call OpenRouter
        response: OpenRouterResponse = await self.openrouter.chat_completion(
            messages=messages,
            model=self._get_model(),
            temperature=self._get_temperature(),
        )

        # 6. Save response message to DB
        agent_message = Message(
            conversation_id=conversation_id,
            author_type="agent",
            agent_id=self.agent_id,
            content=response.content,
            model_used=response.model,
        )
        db.add(agent_message)
        await db.flush()

        # 7. Record token usage
        await record_usage(
            db,
            response=response,
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            conversation_id=conversation_id,
            message_id=agent_message.id,
            project_id=self.project_id,
        )

        await db.commit()
        await db.refresh(agent_message)
        return agent_message
