"""Config: endpoint normalization and secret redaction."""

from __future__ import annotations

import pytest

from pebble.config import Settings, load_settings, normalize_endpoint


def test_endpoint_v1_suffix_is_stripped():
    assert normalize_endpoint("https://x.openai.azure.com/openai/v1") == (
        "https://x.openai.azure.com"
    )
    assert normalize_endpoint("https://x.openai.azure.com/openai/v1/") == (
        "https://x.openai.azure.com"
    )


def test_plain_endpoint_is_untouched():
    assert normalize_endpoint("https://x.openai.azure.com") == "https://x.openai.azure.com"
    assert normalize_endpoint(None) is None
    assert normalize_endpoint("  ") is None


def test_real_env_endpoint_is_normalized():
    settings = load_settings()
    if settings.azure_endpoint:
        assert not settings.azure_endpoint.endswith("/openai/v1")


def test_repr_never_shows_secrets():
    settings = Settings(
        azure_endpoint="https://x.openai.azure.com",
        azure_api_key="super-secret-key",
        azure_deployment="gpt-5-mini",
        azure_speech_key="speech-secret",
    )
    text = repr(settings)
    assert "super-secret-key" not in text
    assert "speech-secret" not in text
    assert "REDACTED" in text
    assert "gpt-5-mini" in text  # non-secret config is still visible


def test_audit_mode_defaults_to_warn(monkeypatch):
    from pebble.config import load_settings

    monkeypatch.delenv("PEBBLE_AUDIT", raising=False)
    assert load_settings().audit_mode == "warn"

    monkeypatch.setenv("PEBBLE_AUDIT", "strict")
    assert load_settings().audit_mode == "strict"

    monkeypatch.setenv("PEBBLE_AUDIT", "shouty")
    from pebble.errors import ConfigError

    with pytest.raises(ConfigError):
        load_settings()


def test_pipeline_version_is_part_of_the_fingerprint(monkeypatch):
    import pebble.models as models
    from tests.conftest import load_sample

    request = load_sample("two_sum.json")
    before = request.request_fingerprint()

    # A bump to the pipeline version must invalidate previously cached videos.
    monkeypatch.setattr(models, "PIPELINE_VERSION", "9")
    assert request.request_fingerprint() != before
