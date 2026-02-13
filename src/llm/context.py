"""Sliding window context management for LLM calls."""

from src.llm.token_counter import count_tokens

# Default token budget (conservative for smaller models)
DEFAULT_MAX_TOKENS = 6000


def build_context(
    conversation_messages: list[dict],
    system_prompt: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[dict]:
    """Build a message list that fits within the token budget.

    Strategy: always include system prompt + first user message + as many
    recent messages as fit within the remaining budget.
    """
    system_msg = {"role": "system", "content": system_prompt}
    system_tokens = count_tokens(system_prompt) + 4

    if not conversation_messages:
        return [system_msg]

    budget = max_tokens - system_tokens

    # Always try to include the first message for context
    first_msg = {"role": conversation_messages[0]["role"], "content": conversation_messages[0]["content"]}
    first_tokens = count_tokens(first_msg["content"]) + 4

    # Build from the end (most recent messages first)
    recent: list[dict] = []
    used = 0

    for msg in reversed(conversation_messages[1:]):
        entry = {"role": msg["role"], "content": msg["content"]}
        msg_tokens = count_tokens(entry["content"]) + 4
        if used + msg_tokens + first_tokens > budget:
            break
        recent.insert(0, entry)
        used += msg_tokens

    # If first message still fits, include it
    if first_tokens <= budget - used:
        return [system_msg, first_msg] + recent
    else:
        return [system_msg] + recent
