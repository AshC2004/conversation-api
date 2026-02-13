"""Approximate token counting using tiktoken."""

import tiktoken

# Use cl100k_base as a reasonable approximation for most models
_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


def count_messages_tokens(messages: list[dict]) -> int:
    total = 0
    for msg in messages:
        total += 4  # message overhead
        total += count_tokens(msg.get("content", ""))
        total += count_tokens(msg.get("role", ""))
    total += 2  # reply priming
    return total
