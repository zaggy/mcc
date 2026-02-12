"""Token counting and context window management using tiktoken."""

import tiktoken

_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in a string using cl100k_base encoding."""
    return len(_encoding.encode(text))


def count_messages_tokens(messages: list[dict[str, str]]) -> int:
    """Approximate token count for a list of chat messages."""
    total = 0
    for msg in messages:
        # ~4 tokens overhead per message for role/separators
        total += 4
        total += count_tokens(msg.get("content", ""))
    return total


def truncate_messages(
    messages: list[dict[str, str]],
    max_tokens: int,
    preserve_recent: int = 10,
) -> list[dict[str, str]]:
    """Truncate messages to fit within max_tokens.

    Always preserves the system prompt (first message) and the most recent
    `preserve_recent` messages. Drops oldest messages from the middle.
    """
    if not messages:
        return messages

    total = count_messages_tokens(messages)
    if total <= max_tokens:
        return messages

    # Separate system prompt, middle, and tail
    system = messages[:1] if messages[0].get("role") == "system" else []
    rest = messages[len(system) :]

    if len(rest) <= preserve_recent:
        return messages

    tail = rest[-preserve_recent:]
    middle = rest[:-preserve_recent]

    # Drop oldest from middle until we fit
    result = system + middle + tail
    while count_messages_tokens(result) > max_tokens and middle:
        middle.pop(0)
        result = system + middle + tail

    return result
