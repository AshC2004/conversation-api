"""LLM client abstraction with Groq (primary) and Google AI (fallback)."""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, messages: list[dict], model: str) -> dict:
        """Return {"content": str, "finish_reason": str, "input_tokens": int, "output_tokens": int}."""
        ...

    @abstractmethod
    async def generate_stream(self, messages: list[dict], model: str) -> AsyncGenerator[dict, None]:
        """Yield {"type": "delta"|"finish", "content"?: str, "finish_reason"?: str, "usage"?: dict}."""
        ...


class GroqClient(LLMClient):
    def __init__(self):
        from groq import AsyncGroq
        settings = get_settings()
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def generate(self, messages: list[dict], model: str) -> dict:
        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,
        )
        choice = response.choices[0]
        return {
            "content": choice.message.content or "",
            "finish_reason": choice.finish_reason,
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
        }

    async def generate_stream(self, messages: list[dict], model: str) -> AsyncGenerator[dict, None]:
        stream = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield {"type": "delta", "content": delta.content}
            if chunk.choices[0].finish_reason:
                yield {
                    "type": "finish",
                    "finish_reason": chunk.choices[0].finish_reason,
                    "usage": {
                        "input_tokens": chunk.x_groq.usage.prompt_tokens if hasattr(chunk, "x_groq") and chunk.x_groq and chunk.x_groq.usage else 0,
                        "output_tokens": chunk.x_groq.usage.completion_tokens if hasattr(chunk, "x_groq") and chunk.x_groq and chunk.x_groq.usage else 0,
                    },
                }


class GoogleAIClient(LLMClient):
    def __init__(self):
        import google.generativeai as genai
        settings = get_settings()
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        self._genai = genai

    def _convert_messages(self, messages: list[dict]) -> tuple[str | None, list[dict]]:
        """Convert OpenAI-style messages to Gemini format."""
        system = None
        history = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                history.append({"role": role, "parts": [msg["content"]]})
        return system, history

    async def generate(self, messages: list[dict], model: str) -> dict:
        system, history = self._convert_messages(messages)
        gen_model = self._genai.GenerativeModel(model, system_instruction=system)
        # Last message is the user prompt; history is everything before
        last = history[-1] if history else {"parts": [""]}
        chat = gen_model.start_chat(history=history[:-1])
        response = await chat.send_message_async(last["parts"][0])
        return {
            "content": response.text,
            "finish_reason": "stop",
            "input_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
        }

    async def generate_stream(self, messages: list[dict], model: str) -> AsyncGenerator[dict, None]:
        system, history = self._convert_messages(messages)
        gen_model = self._genai.GenerativeModel(model, system_instruction=system)
        last = history[-1] if history else {"parts": [""]}
        chat = gen_model.start_chat(history=history[:-1])
        response = await chat.send_message_async(last["parts"][0], stream=True)
        async for chunk in response:
            if chunk.text:
                yield {"type": "delta", "content": chunk.text}
        yield {
            "type": "finish",
            "finish_reason": "stop",
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }


# Singletons
_clients: dict[str, LLMClient] = {}


def get_llm_client(provider: str = "groq") -> LLMClient:
    if provider not in _clients:
        if provider == "groq":
            _clients[provider] = GroqClient()
        elif provider == "google":
            _clients[provider] = GoogleAIClient()
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    return _clients[provider]
