"""@mention parsing and agent resolution."""

import re
import uuid


def parse_mentions(content: str) -> list[str]:
    """Extract @mention tokens from message content.

    Returns lowercased mention tokens. Skips email-like patterns where the
    '@' is preceded by a non-whitespace alphanumeric character.
    """
    # Match @word that is NOT preceded by a word character (to skip emails)
    mentions = re.findall(r"(?<!\w)@(\w+)", content)
    return [m.lower() for m in mentions]


def resolve_mentioned_agents(
    mentions: list[str],
    participants: list[dict],
) -> list[uuid.UUID]:
    """Resolve mention tokens to agent IDs from conversation participants.

    Matches by agent name (case-insensitive) or agent type (e.g. @architect
    matches a participant with type="architect").

    Args:
        mentions: Lowercased mention tokens from parse_mentions().
        participants: Dicts with keys "agent_id", "name", "type".

    Returns:
        List of unique matched agent UUIDs.
    """
    matched: dict[uuid.UUID, None] = {}  # ordered set
    for mention in mentions:
        for p in participants:
            name_lower = p["name"].lower().replace(" ", "")
            type_lower = p["type"].lower()
            if mention == name_lower or mention == type_lower:
                matched[p["agent_id"]] = None
    return list(matched)
