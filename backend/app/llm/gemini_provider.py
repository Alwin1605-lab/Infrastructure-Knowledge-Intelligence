"""Google Gemini LLM provider implementation.

Provides LLM capabilities via the Google Gemini REST API.
Acts as a high-speed fallback provider when Groq rate limits are reached.
"""

import time
from typing import AsyncGenerator

import httpx

from app.config import Settings
from app.core.exceptions import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMGenerationError,
)
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider, LLMResponse
from app.llm.factory import register_provider

logger = get_logger(__name__)


@register_provider("gemini")
class GeminiProvider(BaseLLMProvider):
    """Google Gemini cloud LLM provider."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.get_gemini_api_key()
        if not self._api_key:
            raise LLMConfigurationError(
                "GEMINI_API_KEY or GEMINI_1 is required when using the gemini provider."
            )

        self._model = settings.GEMINI_MODEL
        self._temperature = settings.GEMINI_TEMPERATURE
        self._max_tokens = settings.GEMINI_MAX_TOKENS

        logger.info(
            "gemini_provider_initialized",
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        temp = temperature if temperature is not None else self._temperature
        max_tok = max_tokens if max_tokens is not None else self._max_tokens

        url = f"https://generativelanguage.googleapis.com/v1beta/{self._model}:generateContent?key={self._api_key}"
        if not self._model.startswith("models/"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={self._api_key}"

        payload: dict = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temp,
                "maxOutputTokens": max_tok,
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)

            duration_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 429:
                raise LLMRateLimitError(
                    f"Gemini rate limit exceeded: {response.text}",
                    provider="gemini",
                )
            elif response.status_code != 200:
                raise LLMGenerationError(
                    f"Gemini API returned status {response.status_code}: {response.text}",
                    provider="gemini",
                )

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates or not candidates[0].get("content", {}).get("parts"):
                content = ""
                finish_reason = "empty"
            else:
                content = candidates[0]["content"]["parts"][0].get("text", "")
                finish_reason = candidates[0].get("finishReason", "stop")

            usage_metadata = data.get("usageMetadata", {})
            usage = {
                "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                "total_tokens": usage_metadata.get("totalTokenCount", 0),
            }

            logger.info(
                "gemini_generation_complete",
                model=self._model,
                duration_ms=round(duration_ms, 1),
                tokens=usage.get("total_tokens", 0),
            )

            return LLMResponse(
                content=content,
                model=self._model,
                provider="gemini",
                usage=usage,
                finish_reason=finish_reason,
                raw_response=data,
            )

        except (LLMRateLimitError, LLMGenerationError):
            raise
        except Exception as exc:
            raise LLMGenerationError(
                f"Gemini error: {exc}",
                provider="gemini",
            ) from exc

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        resp = await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        yield resp.content

    def get_langchain_llm(self) -> any:
        return self

    async def health_check(self) -> dict:
        start = time.perf_counter()
        try:
            resp = await self.generate("Health check: reply with OK.", max_tokens=10)
            latency = (time.perf_counter() - start) * 1000
            return {
                "status": "healthy",
                "provider": "gemini",
                "model": self._model,
                "latency_ms": round(latency, 2),
            }
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            return {
                "status": "unhealthy",
                "provider": "gemini",
                "model": self._model,
                "latency_ms": round(latency, 2),
                "error": str(exc),
            }
