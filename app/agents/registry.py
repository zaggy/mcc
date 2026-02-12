"""Agent registry and factory for creating agent instances by type."""

from app.agents.base import BaseAgent
from app.db.models import Agent
from app.services.openrouter import OpenRouterClient

# Populated by imports below; maps agent type string → BaseAgent subclass
AGENT_REGISTRY: dict[str, type[BaseAgent]] = {}


def register_agent(agent_type: str):
    """Decorator to register an agent class for a given type."""

    def wrapper(cls: type[BaseAgent]) -> type[BaseAgent]:
        AGENT_REGISTRY[agent_type] = cls
        return cls

    return wrapper


def create_agent(agent_record: Agent, openrouter: OpenRouterClient) -> BaseAgent:
    """Factory: create an agent instance from its DB record."""
    cls = AGENT_REGISTRY.get(agent_record.type)
    if cls is None:
        raise ValueError(f"Unknown agent type: {agent_record.type!r}")
    return cls(agent_record=agent_record, openrouter=openrouter)


def _load_agents() -> None:
    """Import agent modules to trigger registration."""
    import app.agents.architect  # noqa: F401
    import app.agents.coder  # noqa: F401
    import app.agents.orchestrator  # noqa: F401
    import app.agents.reviewer  # noqa: F401
    import app.agents.tester  # noqa: F401


_load_agents()
