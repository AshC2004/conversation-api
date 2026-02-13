"""System prompt templates."""

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, concise AI assistant. Provide clear, well-structured responses. "
    "When appropriate, use markdown formatting for readability. "
    "If you're unsure about something, say so rather than guessing."
)

TITLE_GENERATION_PROMPT = (
    "Generate a concise title (max 8 words) for a conversation that starts with the following message. "
    "Return ONLY the title text, nothing else."
)

THINKING_PROMPT_PREFIX = (
    "Think step by step. Show your reasoning in <thinking> tags before giving your final answer.\n\n"
)


def build_system_prompt(custom_prompt: str | None = None, thinking: bool = False) -> str:
    prompt = custom_prompt or DEFAULT_SYSTEM_PROMPT
    if thinking:
        prompt = THINKING_PROMPT_PREFIX + prompt
    return prompt
