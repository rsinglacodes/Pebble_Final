"""TTS: sanitization, voice resolution and synthesis plumbing (no network)."""

from __future__ import annotations

import pytest

from pebble.config import Settings, voice_for_language
from pebble.errors import ConfigError, TTSError
from pebble.tts import sanitize_narration, synthesize_scene
from tests.conftest import wav_bytes

SPEECH_SETTINGS = Settings(azure_speech_key="dummy-key", azure_speech_region="dummy-region")


def test_sanitize_removes_markdown_characters():
    assert sanitize_narration("**Bold** and `code` and # Heading") == "Bold and code and Heading"
    assert sanitize_narration("_emphasis_ text") == "emphasis text"


def test_sanitize_keeps_identifiers_and_collapses_whitespace():
    assert sanitize_narration("nums at index i") == "nums at index i"
    assert sanitize_narration("two_sum\n\n  is  here") == "two_sum is here"


def test_sanitize_handles_empty_input():
    assert sanitize_narration("") == ""
    assert sanitize_narration("   \n ") == ""


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("English", "en-IN-NeerjaNeural"),
        ("english", "en-IN-NeerjaNeural"),
        ("Hindi", "hi-IN-SwaraNeural"),
        ("Spanish", "es-ES-ElviraNeural"),
        ("French", "fr-FR-DeniseNeural"),
        ("German", "de-DE-KatjaNeural"),
    ],
)
def test_known_languages_map_to_voices(monkeypatch, language, expected):
    monkeypatch.delenv("AZURE_SPEECH_VOICE", raising=False)
    assert voice_for_language(language) == expected


def test_env_voice_overrides_everything(monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_VOICE", "en-US-JennyNeural")
    assert voice_for_language("English") == "en-US-JennyNeural"
    assert voice_for_language("Klingon") == "en-US-JennyNeural"


def test_unmapped_language_raises_config_error(monkeypatch):
    monkeypatch.delenv("AZURE_SPEECH_VOICE", raising=False)
    with pytest.raises(ConfigError) as excinfo:
        voice_for_language("Klingon")
    message = str(excinfo.value)
    assert "Klingon" in message
    assert "AZURE_SPEECH_VOICE" in message


def test_synthesize_scene_writes_a_wav(monkeypatch, tmp_path):
    calls = []

    def fake_synth(text, voice, settings):
        calls.append((text, voice))
        return wav_bytes(0.6)

    monkeypatch.setattr("pebble.tts._synth_audio", fake_synth)

    out = tmp_path / "01_Scene1.wav"
    duration = synthesize_scene("**Hello** there.", out, "en-IN-NeerjaNeural", SPEECH_SETTINGS)

    assert out.exists() and out.stat().st_size > 0
    assert abs(duration - 0.6) < 0.1
    assert calls == [("Hello there.", "en-IN-NeerjaNeural")]


def test_transient_failure_is_retried(monkeypatch, tmp_path):
    attempts = {"count": 0}

    def flaky(text, voice, settings):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise TTSError("connection reset by peer")
        return wav_bytes(0.4)

    monkeypatch.setattr("pebble.tts._synth_audio", flaky)

    duration = synthesize_scene("Hello.", tmp_path / "a.wav", "voice", SPEECH_SETTINGS)
    assert attempts["count"] == 3
    assert duration > 0


def test_permanent_failure_is_not_retried(monkeypatch, tmp_path):
    attempts = {"count": 0}

    def broken(text, voice, settings):
        attempts["count"] += 1
        raise TTSError("401 authentication failed")

    monkeypatch.setattr("pebble.tts._synth_audio", broken)

    with pytest.raises(TTSError):
        synthesize_scene("Hello.", tmp_path / "a.wav", "voice", SPEECH_SETTINGS)
    assert attempts["count"] == 1


def test_empty_narration_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr("pebble.tts._synth_audio", lambda *a: wav_bytes(0.3))
    with pytest.raises(TTSError):
        synthesize_scene("##  ", tmp_path / "a.wav", "voice", SPEECH_SETTINGS)


def test_cancellation_text_works_without_a_from_result_helper(monkeypatch):
    """The installed SDK (1.53) only exposes the constructor; older docs differ."""
    import azure.cognitiveservices.speech as speechsdk

    from pebble import tts

    class FakeDetails:
        def __init__(self, result):
            self.reason = "Error"
            self.error_code = "ServiceTimeout"
            self.error_details = "the service timed out"

    monkeypatch.setattr(speechsdk, "SpeechSynthesisCancellationDetails", FakeDetails)
    text = tts._cancellation_text(object())
    assert "ServiceTimeout" in text
    assert "the service timed out" in text
