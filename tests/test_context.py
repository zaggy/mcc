"""Tests for token counting and context window management."""

from app.agents.context import count_messages_tokens, count_tokens, truncate_messages


def test_count_tokens_empty():
    assert count_tokens("") == 0


def test_count_tokens_simple():
    result = count_tokens("Hello, world!")
    assert result > 0
    assert isinstance(result, int)


def test_count_tokens_longer_text():
    short = count_tokens("Hi")
    long = count_tokens("This is a much longer sentence with many more tokens in it.")
    assert long > short


def test_count_messages_tokens_empty():
    assert count_messages_tokens([]) == 0


def test_count_messages_tokens_single():
    messages = [{"role": "system", "content": "You are helpful."}]
    result = count_messages_tokens(messages)
    # At least the overhead (4) plus the content tokens
    assert result > 4


def test_count_messages_tokens_multiple():
    messages = [
        {"role": "system", "content": "System prompt."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    result = count_messages_tokens(messages)
    assert result > 12  # 3 messages × 4 overhead


def test_truncate_no_truncation_needed():
    messages = [
        {"role": "system", "content": "Short."},
        {"role": "user", "content": "Hi"},
    ]
    result = truncate_messages(messages, max_tokens=10000)
    assert result == messages


def test_truncate_empty():
    assert truncate_messages([], max_tokens=100) == []


def test_truncate_preserves_system_and_recent():
    system = {"role": "system", "content": "System prompt."}
    old_msgs = [{"role": "user", "content": f"Old message {i}"} for i in range(20)]
    recent = [{"role": "user", "content": f"Recent message {i}"} for i in range(10)]
    messages = [system] + old_msgs + recent

    # Set a token limit that forces truncation
    total_tokens = count_messages_tokens(messages)
    result = truncate_messages(messages, max_tokens=total_tokens // 2)

    # System prompt preserved
    assert result[0] == system
    # Recent messages preserved (last 10)
    assert result[-10:] == recent
    # Some old messages were dropped
    assert len(result) < len(messages)


def test_truncate_preserves_all_when_few_messages():
    messages = [
        {"role": "system", "content": "System."},
        {"role": "user", "content": "One"},
        {"role": "user", "content": "Two"},
    ]
    # Even with a tiny limit, we don't remove the only messages
    result = truncate_messages(messages, max_tokens=1, preserve_recent=10)
    assert len(result) == len(messages)
