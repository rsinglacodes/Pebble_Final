"""Azure OpenAI chat wrapper.

One user message per call (no system role) so the template is the single
source of truth. Parameter handling is tolerant of model differences.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from pebble.config import Settings
from pebble.errors import PebbleError, TruncatedOutputError

logger = logging.getLogger(__name__)

TIMEOUT = 300.0
MAX_RETRIES = 2


@dataclass(frozen=True)
class LLMUsage:
    """Token counts reported by the API (None when the API omits them)."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None

    @property
    def known(self) -> bool:
        return self.prompt_tokens is not None or self.completion_tokens is not None


@dataclass(frozen=True)
class LLMResponse:
    """One chat completion: the text plus what it cost and how long it took."""

    text: str
    usage: LLMUsage | None = None
    seconds: float = 0.0
    finish_reason: str | None = None

    def __str__(self) -> str:  # keeps `print(reply)` / len(reply) usable
        return self.text

    def __len__(self) -> int:
        return len(self.text)


def _usage_from(response: Any) -> LLMUsage | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "completion_tokens", None)
    details = getattr(usage, "completion_tokens_details", None)
    reasoning = getattr(details, "reasoning_tokens", None) if details is not None else None
    if prompt is None and completion is None and reasoning is None:
        return None
    return LLMUsage(
        prompt_tokens=prompt, completion_tokens=completion, reasoning_tokens=reasoning
    )

_PARAM_ERROR_MARKERS = ("unsupported", "invalid", "unknown", "not allowed", "unexpected", "does not support")


def _is_param_error(exc: Exception, param: str) -> bool:
    """True when the API rejected a request *parameter* rather than the content."""
    text = str(exc).lower()
    if param.lower() not in text:
        return False
    return any(marker in text for marker in _PARAM_ERROR_MARKERS)


class LLMClient:
    """Thin wrapper around AzureOpenAI."""

    def __init__(self, settings: Settings) -> None:
        from openai import AzureOpenAI

        if not settings.azure_endpoint:
            raise PebbleError("Azure OpenAI endpoint is not configured (AZURE_OPENAI_ENDPOINT)")
        if not settings.azure_api_key:
            raise PebbleError("Azure OpenAI API key is not configured (AZURE_API_KEY)")
        if not settings.azure_deployment:
            raise PebbleError("Azure OpenAI deployment is not configured (AZURE_OPENAI_DEPLOYMENT)")

        self.deployment = settings.azure_deployment
        self.max_output_tokens = settings.max_output_tokens
        # Some deployments reject temperature; remember the rejection so later
        # calls (retries, repairs) do not pay for the same failed request again.
        self.use_temperature = True
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
            api_version=settings.azure_api_version or "2024-10-21",
            timeout=TIMEOUT,
            max_retries=MAX_RETRIES,
        )

    # -- request helpers --------------------------------------------------
    def _token_kwargs(self) -> dict[str, Any]:
        if self.max_output_tokens:
            return {"max_completion_tokens": self.max_output_tokens}
        return {}

    def _create(
        self, prompt: str, use_temperature: bool, token_key: str | None
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.deployment,
            "messages": [{"role": "user", "content": prompt}],
        }
        if use_temperature:
            kwargs["temperature"] = 0
        if token_key:
            kwargs[token_key] = self.max_output_tokens
        started = time.monotonic()
        response = self._client.chat.completions.create(**kwargs)
        seconds = time.monotonic() - started
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise TruncatedOutputError(
                "The LLM response was truncated by the token limit (finish_reason='length'). "
                "Raise PEBBLE_MAX_OUTPUT_TOKENS or shorten the requested style."
            )
        text = choice.message.content or ""
        if not text.strip():
            raise PebbleError("LLM returned an empty response")
        return LLMResponse(
            text=text,
            usage=_usage_from(response),
            seconds=seconds,
            finish_reason=choice.finish_reason,
        )

    def call_llm(self, prompt: str) -> LLMResponse:
        """Send the prompt as a single user message and return text + usage."""
        temperature = self.use_temperature
        token_key = "max_completion_tokens" if self.max_output_tokens else None

        for _ in range(4):
            try:
                return self._create(prompt, temperature, token_key)
            except TruncatedOutputError:
                raise
            except PebbleError:
                raise
            except Exception as exc:  # noqa: BLE001 - normalize API parameter errors
                if _is_param_error(exc, "temperature") and temperature:
                    logger.warning("API rejected temperature=0; retrying without it")
                    temperature = False
                    self.use_temperature = False
                    continue
                if token_key == "max_completion_tokens" and _is_param_error(
                    exc, "max_completion_tokens"
                ):
                    logger.warning("API rejected max_completion_tokens; falling back to max_tokens")
                    token_key = "max_tokens"
                    continue
                if token_key and _is_param_error(exc, token_key):
                    logger.warning("API rejected %s; dropping the token limit", token_key)
                    token_key = None
                    continue
                raise
        raise PebbleError("LLM call failed after exhausting parameter fallbacks")


def make_client(settings: Settings) -> LLMClient:
    return LLMClient(settings)
