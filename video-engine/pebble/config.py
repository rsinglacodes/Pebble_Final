"""Configuration loaded from the project-root .env file.

Only the *names* of the environment variables are part of Pebble's contract;
values are never logged, printed, repr()ed or written to disk by Pebble.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from pebble.errors import ConfigError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Canonical env var names -> accepted aliases (first non-empty wins).
AZURE_ENDPOINT_KEYS = ("AZURE_OPENAI_ENDPOINT",)
AZURE_API_KEY_KEYS = ("AZURE_API_KEY", "AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT_KEYS = ("AZURE_OPENAI_DEPLOYMENT",)
AZURE_API_VERSION_KEYS = ("AZURE_OPENAI_API_VERSION",)
AZURE_SPEECH_KEY_KEYS = ("AZURE_SPEECH_KEY",)
AZURE_SPEECH_REGION_KEYS = ("AZURE_SPEECH_REGION",)

REQUIRED_NAME_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("AZURE_OPENAI_ENDPOINT", AZURE_ENDPOINT_KEYS),
    ("AZURE_API_KEY", AZURE_API_KEY_KEYS),
    ("AZURE_OPENAI_DEPLOYMENT", AZURE_DEPLOYMENT_KEYS),
    ("AZURE_OPENAI_API_VERSION", AZURE_API_VERSION_KEYS),
    ("AZURE_SPEECH_KEY", AZURE_SPEECH_KEY_KEYS),
    ("AZURE_SPEECH_REGION", AZURE_SPEECH_REGION_KEYS),
)

# explanation_language (lower-cased) -> Azure Speech voice name.
VOICE_MAP: dict[str, str] = {
    "english": "en-IN-NeerjaNeural",
    "hindi": "hi-IN-SwaraNeural",
    "spanish": "es-ES-ElviraNeural",
    "french": "fr-FR-DeniseNeural",
    "german": "de-DE-KatjaNeural",
}

AZURE_SPEECH_VOICE_KEY = "AZURE_SPEECH_VOICE"

# Bump when the *meaning* of a generated video changes (visuals, pacing,
# narration), so previously cached videos for the same request are not reused.
PIPELINE_VERSION = "1"

# Layout audit mode for a render: "warn" logs issues, "strict" fails the scene.
AUDIT_MODE_KEY = "PEBBLE_AUDIT"
AUDIT_MODES = ("warn", "strict")
DEFAULT_AUDIT_MODE = "warn"

# Cost prices, USD per 1M units. Defaults are estimates: verify them against
# the Azure OpenAI and Azure Speech pricing pages before trusting a total.
LLM_INPUT_PRICE_KEY = "LLM_INPUT_PRICE_PER_1M"
LLM_OUTPUT_PRICE_KEY = "LLM_OUTPUT_PRICE_PER_1M"
TTS_PRICE_KEY = "TTS_PRICE_PER_1M_CHARS"
USD_TO_INR_KEY = "USD_TO_INR"

DEFAULT_LLM_INPUT_PRICE = 0.25
DEFAULT_LLM_OUTPUT_PRICE = 2.00
DEFAULT_TTS_PRICE = 16.00

_SECRET_KEY_NAMES = {"key", "token", "secret", "password", "connection_string"}
REDACTED = "***REDACTED***"

_loaded = False


def load_env() -> None:
    """Load .env from the project root once (idempotent)."""
    global _loaded
    if _loaded:
        return
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=False)
    else:
        load_dotenv(override=False)
    _loaded = True


def first_env(keys: tuple[str, ...]) -> str | None:
    for name in keys:
        value = os.environ.get(name)
        if value is not None and value.strip():
            return value
    return None


def normalize_endpoint(value: str | None) -> str | None:
    """Return a resource-level Azure OpenAI endpoint.

    AZURE_OPENAI_ENDPOINT may be written as an OpenAI-style base URL ending in
    ``/openai/v1`` (the Azure "v1" API surface). The openai SDK builds the
    classic ``/openai/deployments/{deployment}/...`` path itself, so that suffix
    must be removed or the request URL ends up doubled and 404s.
    """
    if not value:
        return None
    cleaned = value.strip().rstrip("/")
    if cleaned.endswith("/openai/v1"):
        cleaned = cleaned[: -len("/openai/v1")]
    return cleaned.rstrip("/") or None


def speech_voice_override() -> str | None:
    """The AZURE_SPEECH_VOICE override, if set (its value is never logged)."""
    load_env()
    return first_env((AZURE_SPEECH_VOICE_KEY,))


def supported_languages() -> list[str]:
    """Display names of the explanation languages that have a configured voice."""
    return [name.title() for name in sorted(VOICE_MAP)]


def is_supported_language(language: str | None) -> bool:
    """True when a language has a voice; a configured override accepts any."""
    if speech_voice_override() is not None:
        return True
    return (language or "").strip().lower() in VOICE_MAP


def voice_for_language(language: str | None) -> str:
    """Resolve the Azure Speech voice for an explanation language.

    AZURE_SPEECH_VOICE wins over everything; otherwise the language is looked up
    in VOICE_MAP. An unmapped language is an error: silently narrating a Hindi
    video with an English voice is worse than failing.
    """
    load_env()
    override = first_env((AZURE_SPEECH_VOICE_KEY,))
    if override:
        return override.strip()

    key = (language or "").strip().lower()
    if key in VOICE_MAP:
        return VOICE_MAP[key]

    raise ConfigError(
        f"No Azure Speech voice configured for explanation language {language!r}. "
        f"Known languages: {', '.join(sorted(VOICE_MAP))}. "
        f"Add the language to VOICE_MAP in pebble/config.py, "
        f"or set {AZURE_SPEECH_VOICE_KEY} to a full voice name "
        f"(for example en-US-JennyNeural) to override the map."
    )


def env_name_present(keys: tuple[str, ...]) -> bool:
    """True when at least one alias exists and is non-empty (value never returned)."""
    return first_env(keys) is not None


def redact(value: object, keep: int = 0) -> str:
    """Return a safe representation of a possibly-secret value."""
    if value is None:
        return "None"
    text = str(value)
    if keep and len(text) > keep:
        return text[:keep] + "…" + REDACTED
    return REDACTED


@dataclass(frozen=True)
class Settings:
    azure_endpoint: str | None = None
    azure_api_key: str | None = field(default=None, repr=False)
    azure_deployment: str | None = None
    azure_api_version: str | None = None
    azure_speech_key: str | None = field(default=None, repr=False)
    azure_speech_region: str | None = None
    render_quality: str = "m"
    audit_mode: str = DEFAULT_AUDIT_MODE
    max_generation_attempts: int = 3
    max_render_retries: int = 3
    max_output_tokens: int | None = None
    llm_input_price_per_1m: float = DEFAULT_LLM_INPUT_PRICE
    llm_output_price_per_1m: float = DEFAULT_LLM_OUTPUT_PRICE
    tts_price_per_1m_chars: float = DEFAULT_TTS_PRICE
    usd_to_inr: float | None = None

    def __repr__(self) -> str:
        # Secrets never appear in repr / logs.
        return (
            "Settings("
            f"azure_endpoint={self.azure_endpoint!r}, "
            f"azure_api_key={redact(self.azure_api_key)}, "
            f"azure_deployment={self.azure_deployment!r}, "
            f"azure_api_version={self.azure_api_version!r}, "
            f"azure_speech_key={redact(self.azure_speech_key)}, "
            f"azure_speech_region={self.azure_speech_region!r}, "
            f"render_quality={self.render_quality!r}, "
            f"audit_mode={self.audit_mode!r}, "
            f"max_generation_attempts={self.max_generation_attempts!r}, "
            f"max_render_retries={self.max_render_retries!r}, "
            f"max_output_tokens={self.max_output_tokens!r}, "
            f"llm_input_price_per_1m={self.llm_input_price_per_1m!r}, "
            f"llm_output_price_per_1m={self.llm_output_price_per_1m!r}, "
            f"tts_price_per_1m_chars={self.tts_price_per_1m_chars!r}, "
            f"usd_to_inr={self.usd_to_inr!r})"
        )

    @property
    def missing_required_names(self) -> list[str]:
        """Names of required env vars that are absent or empty (no values)."""
        return [name for name, keys in REQUIRED_NAME_GROUPS if not env_name_present(keys)]

    @property
    def required_names_present(self) -> bool:
        return not self.missing_required_names


def _non_negative_int(raw: str | None, default: int, name: str) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if value < 0:
        raise ConfigError(f"{name} must be >= 0, got {value}")
    return value


def _positive_int(raw: str | None, default: int, name: str) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if value < 1:
        raise ConfigError(f"{name} must be >= 1, got {value}")
    return value


def _positive_float(raw: str | None, default: float, name: str) -> float:
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc
    if value < 0:
        raise ConfigError(f"{name} must be >= 0, got {value}")
    return value


def _optional_float(raw: str | None, name: str) -> float | None:
    if raw is None or not raw.strip():
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc
    if value <= 0:
        raise ConfigError(f"{name} must be > 0, got {value}")
    return value


def load_settings() -> Settings:
    """Read settings from the environment (.env already loaded)."""
    load_env()
    quality = (os.environ.get("RENDER_QUALITY") or "m").strip().lower()
    if quality not in {"l", "m", "h"}:
        raise ConfigError(f"RENDER_QUALITY must be one of l/m/h, got {quality!r}")

    audit_mode = (os.environ.get(AUDIT_MODE_KEY) or DEFAULT_AUDIT_MODE).strip().lower()
    if audit_mode not in AUDIT_MODES:
        raise ConfigError(
            f"{AUDIT_MODE_KEY} must be one of {'/'.join(AUDIT_MODES)}, got {audit_mode!r}"
        )

    tokens_raw = os.environ.get("PEBBLE_MAX_OUTPUT_TOKENS")
    tokens: int | None = None
    if tokens_raw is not None and tokens_raw.strip():
        tokens = _positive_int(tokens_raw, 0, "PEBBLE_MAX_OUTPUT_TOKENS")

    return Settings(
        azure_endpoint=normalize_endpoint(first_env(AZURE_ENDPOINT_KEYS)),
        azure_api_key=first_env(AZURE_API_KEY_KEYS),
        azure_deployment=first_env(AZURE_DEPLOYMENT_KEYS),
        azure_api_version=first_env(AZURE_API_VERSION_KEYS),
        azure_speech_key=first_env(AZURE_SPEECH_KEY_KEYS),
        azure_speech_region=first_env(AZURE_SPEECH_REGION_KEYS),
        render_quality=quality,
        audit_mode=audit_mode,
        max_generation_attempts=_positive_int(
            os.environ.get("MAX_GENERATION_ATTEMPTS"), 3, "MAX_GENERATION_ATTEMPTS"
        ),
        max_render_retries=_non_negative_int(
            os.environ.get("MAX_RENDER_RETRIES"), 3, "MAX_RENDER_RETRIES"
        ),
        max_output_tokens=tokens,
        llm_input_price_per_1m=_positive_float(
            os.environ.get(LLM_INPUT_PRICE_KEY), DEFAULT_LLM_INPUT_PRICE, LLM_INPUT_PRICE_KEY
        ),
        llm_output_price_per_1m=_positive_float(
            os.environ.get(LLM_OUTPUT_PRICE_KEY), DEFAULT_LLM_OUTPUT_PRICE, LLM_OUTPUT_PRICE_KEY
        ),
        tts_price_per_1m_chars=_positive_float(
            os.environ.get(TTS_PRICE_KEY), DEFAULT_TTS_PRICE, TTS_PRICE_KEY
        ),
        usd_to_inr=_optional_float(os.environ.get(USD_TO_INR_KEY), USD_TO_INR_KEY),
    )
