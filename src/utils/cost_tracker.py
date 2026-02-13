"""LLM cost estimation and tracking."""

import logging

logger = logging.getLogger(__name__)

# Price per 1K tokens (USD) — approximate as of early 2026
MODEL_PRICING: dict[str, dict[str, float]] = {
    "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
    "llama-3.1-70b-versatile": {"input": 0.00059, "output": 0.00079},
    "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},
    "mixtral-8x7b-32768": {"input": 0.00024, "output": 0.00024},
    "gemma2-9b-it": {"input": 0.00020, "output": 0.00020},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
}

# Fallback pricing for unknown models
DEFAULT_PRICING = {"input": 0.0005, "output": 0.001}


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate cost in USD for a single LLM call."""
    pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
    cost = (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]
    return round(cost, 8)


def log_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate and log the cost of an LLM call."""
    cost = estimate_cost(input_tokens, output_tokens, model)
    logger.info(
        "LLM cost: model=%s input_tokens=%d output_tokens=%d cost=$%.6f",
        model, input_tokens, output_tokens, cost,
    )
    return cost
