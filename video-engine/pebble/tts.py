"""Narration to speech via Azure Speech, one synthesizer per scene."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pebble.config import Settings, voice_for_language
from pebble.cost import CostTracker
from pebble.errors import ConfigError, TTSError
from pebble.models import GenerationResult
from pebble.mux import probe_duration
from pebble.workspace import JobWorkspace

logger = logging.getLogger(__name__)

MAX_TRANSIENT_RETRIES = 2

_EMPHASIS_RE = re.compile(r"(?<![\w])_([^_\n]+)_(?![\w])")
_SPACE_RE = re.compile(r"\s+")

_PERMANENT_MARKERS = (
    "401",
    "403",
    "authentication",
    "unauthorized",
    "forbidden",
    "invalid subscription",
    "quota",
)


@dataclass(frozen=True)
class SceneAudio:
    index: int
    class_name: str
    audio_path: Path
    duration: float
    text: str


def sanitize_narration(text: str) -> str:
    """Strip markdown so it is not read aloud, and collapse whitespace."""
    cleaned = (text or "").replace("`", "")
    cleaned = cleaned.replace("**", "").replace("*", "")
    cleaned = cleaned.replace("#", "")
    cleaned = _EMPHASIS_RE.sub(r"\1", cleaned)
    cleaned = _SPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def _speech_config(settings: Settings, voice: str):
    """Build an Azure SpeechConfig. Imported lazily so tests need no SDK call."""
    import azure.cognitiveservices.speech as speechsdk

    if not settings.azure_speech_key:
        raise ConfigError("AZURE_SPEECH_KEY is not configured")
    if not settings.azure_speech_region:
        raise ConfigError("AZURE_SPEECH_REGION is not configured")

    config = speechsdk.SpeechConfig(
        subscription=settings.azure_speech_key, region=settings.azure_speech_region
    )
    config.speech_synthesis_voice_name = voice
    return config


def _synth_audio(text: str, voice: str, settings: Settings) -> bytes:
    """Synthesize `text` and return WAV bytes. Isolated for easy mocking."""
    import azure.cognitiveservices.speech as speechsdk

    speech_config = _speech_config(settings, voice)
    # audio_config=None returns the audio in memory instead of playing it.
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return bytes(result.audio_data)

    if result.reason == speechsdk.ResultReason.Canceled:
        raise TTSError(f"Azure Speech canceled the synthesis: {_cancellation_text(result)}")

    raise TTSError(f"Azure Speech returned an unexpected result: {result.reason}")


def _cancellation_text(result) -> str:
    """Explain a canceled result without depending on one SDK's helper name."""
    details = None
    try:
        import azure.cognitiveservices.speech as speechsdk

        factory = getattr(speechsdk.SpeechSynthesisCancellationDetails, "from_result", None)
        if factory is not None:
            details = factory(result)
        else:
            details = speechsdk.SpeechSynthesisCancellationDetails(result)
    except Exception:  # noqa: BLE001 - diagnostics must never mask the failure
        details = getattr(result, "cancellation_details", None)

    reason = getattr(details, "reason", None)
    code = getattr(details, "error_code", None)
    message = getattr(details, "error_details", "") or "no details"
    return f"reason={reason} error_code={code}: {message}"


def _is_permanent(error: str) -> bool:
    lowered = (error or "").lower()
    return any(marker in lowered for marker in _PERMANENT_MARKERS)


def _synthesize_with_retries(text: str, voice: str, settings: Settings) -> bytes:
    last_error = ""
    for attempt in range(MAX_TRANSIENT_RETRIES + 1):
        try:
            return _synth_audio(text, voice, settings)
        except ConfigError:
            raise
        except TTSError as exc:
            last_error = str(exc)
            if _is_permanent(last_error) or "canceled the synthesis" in last_error:
                # A cancellation is the service's verdict, not a flaky call: retrying
                # it only burns time (and has crashed the native SDK).
                raise
            if attempt < MAX_TRANSIENT_RETRIES:
                logger.warning(
                    "speech synthesis failed (attempt %d/%d), retrying: %s",
                    attempt + 1,
                    MAX_TRANSIENT_RETRIES + 1,
                    last_error,
                )
        except Exception as exc:  # noqa: BLE001 - network/SDK errors are transient here
            last_error = f"{type(exc).__name__}: {exc}"
            if _is_permanent(last_error):
                raise TTSError(last_error) from exc
            if attempt < MAX_TRANSIENT_RETRIES:
                logger.warning(
                    "speech synthesis error (attempt %d/%d), retrying: %s",
                    attempt + 1,
                    MAX_TRANSIENT_RETRIES + 1,
                    last_error,
                )
    raise TTSError(f"speech synthesis failed after retries: {last_error}")


def synthesize_scene(
    narration: str, out_path: Path, voice: str, settings: Settings
) -> float:
    """Write one scene's narration to `out_path` and return its duration."""
    text = sanitize_narration(narration)
    if not text:
        raise TTSError(f"narration for {out_path.stem} is empty after sanitizing")

    audio = _synthesize_with_retries(text, voice, settings)
    if not audio:
        raise TTSError(f"Azure Speech returned no audio for {out_path.stem}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    return probe_duration(out_path)


def narrate_scenes(
    result: GenerationResult,
    workspace: JobWorkspace,
    settings: Settings,
    language: str,
    on_scene: Callable[[SceneAudio], None] | None = None,
    cost: CostTracker | None = None,
) -> list[SceneAudio]:
    """Synthesize every scene's narration in order."""
    voice = voice_for_language(language)
    total = len(result.scenes)
    logger.info("narrating %d scene(s) with voice %s", total, voice)

    audio: list[SceneAudio] = []
    for index, scene in enumerate(result.scenes, start=1):
        out_path = workspace.audio_dir / f"{index:02d}_{scene.class_name}.wav"
        started = time.monotonic()
        duration = synthesize_scene(scene.narration, out_path, voice, settings)
        text = sanitize_narration(scene.narration)
        item = SceneAudio(
            index=index,
            class_name=scene.class_name,
            audio_path=out_path,
            duration=duration,
            text=text,
        )
        audio.append(item)
        if cost is not None:
            cost.record_tts(scene.class_name, len(text), voice)
        logger.info(
            "[narrate %d/%d] %s  %d chars -> %.2fs audio  %.1fs",
            index,
            total,
            scene.class_name,
            len(text),
            duration,
            time.monotonic() - started,
        )
        if on_scene is not None:
            on_scene(item)
    return audio
