"""Blob storage: layout, ordering, retries, cache and config errors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pebble.errors import ConfigError
from pebble.storage import (
    BlobConfig,
    BlobStorage,
    anonymous_get,
    load_blob_config,
    storage_configured,
)

CONNECTION = "DefaultEndpointsProtocol=https;AccountName=pebbletest;AccountKey=fake==;"


class FakeBlob:
    def __init__(self, store: dict[str, bytes], key: str) -> None:
        self.store = store
        self.key = key

    def get_blob_properties(self):
        if self.key not in self.store:
            raise KeyError(self.key)
        return _Props(len(self.store[self.key]))

    def download_blob(self):
        if self.key not in self.store:
            raise KeyError(self.key)
        return _Body(self.store[self.key])


class _Props:
    def __init__(self, size: int) -> None:
        self.size = size


class _Body:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def readall(self) -> bytes:
        return self._data


class FakeContainer:
    def __init__(self, store: dict[str, bytes], fail_uploads: int = 0) -> None:
        self.store = store
        self.fail_uploads = fail_uploads
        self.public_access = None
        self.upload_order: list[str] = []

    def set_container_access_policy(self, signed_identifiers, public_access):
        self.public_access = public_access

    def upload_blob(self, name, data, overwrite=False, content_settings=None):
        if self.fail_uploads > 0:
            self.fail_uploads -= 1
            raise OSError("transient upload failure")
        self.store[name] = bytes(data)
        self.upload_order.append(name)

    def get_blob_client(self, key):
        return FakeBlob(self.store, key)

    def delete_blob(self, key):
        if key not in self.store:
            raise KeyError(key)
        del self.store[key]

    def get_container_properties(self):
        return {"name": "videos"}


class FakeService:
    def __init__(self, store: dict[str, bytes] | None = None, fail_uploads: int = 0) -> None:
        self.store = store if store is not None else {}
        self.container = FakeContainer(self.store, fail_uploads=fail_uploads)

    def get_container_client(self, name):
        return self.container


def _config(**changes) -> BlobConfig:
    base = {
        "container": "videos",
        "connection_string": CONNECTION,
        "account_name": "pebbletest",
        "account_key": "fake==",
        "public_base_url": None,
    }
    base.update(changes)
    return BlobConfig(**base)


def _storage(service=None, fetcher=None) -> BlobStorage:
    return BlobStorage(_config(), service=service or FakeService(), fetcher=fetcher)


# ---------------------------------------------------------------------------
# keys and URLs
# ---------------------------------------------------------------------------


def test_keys_are_grouped_by_fingerprint():
    storage = _storage()
    assert storage.video_key("abc") == "videos/abc/final.mp4"
    assert storage.metadata_key("abc") == "videos/abc/metadata.json"
    assert storage.result_key("abc") == "videos/abc/result.json"
    assert storage.public_url("videos/abc/final.mp4") == (
        "https://pebbletest.blob.core.windows.net/videos/videos/abc/final.mp4"
    )


def test_public_base_url_override_is_used():
    storage = BlobStorage(
        _config(public_base_url="https://cdn.example.com/"), service=FakeService()
    )
    assert storage.public_url("a/b.mp4") == "https://cdn.example.com/videos/a/b.mp4"


def test_host_only_base_url_gets_the_container_appended():
    storage = BlobStorage(
        _config(
            public_base_url="https://acct.blob.core.windows.net", account_name="acct"
        ),
        service=FakeService(),
    )
    assert storage.public_url("videos/fp/final.mp4") == (
        "https://acct.blob.core.windows.net/videos/videos/fp/final.mp4"
    )


def test_container_scoped_base_url_is_not_doubled():
    storage = BlobStorage(
        _config(public_base_url="https://acct.blob.core.windows.net/videos"),
        service=FakeService(),
    )
    assert storage.public_url("videos/fp/final.mp4") == (
        "https://acct.blob.core.windows.net/videos/videos/fp/final.mp4"
    )


# ---------------------------------------------------------------------------
# uploads
# ---------------------------------------------------------------------------


def _video(path: Path, size: int = 2048) -> Path:
    path.write_bytes(b"\x00" * size)
    return path


def test_upload_bundle_writes_result_last(tmp_path):
    service = FakeService()
    storage = _storage(service)
    video = _video(tmp_path / "final.mp4")

    url = storage.upload_job_bundle(
        "fp1",
        video,
        {"scenes": []},
        {"video_url": "u", "solution": {"code": "x"}},
    )

    order = service.container.upload_order
    assert order == ["videos/fp1/final.mp4", "videos/fp1/metadata.json", "videos/fp1/result.json"]
    assert url == "https://pebbletest.blob.core.windows.net/videos/videos/fp1/final.mp4"
    stored = json.loads(service.store["videos/fp1/result.json"].decode("utf-8"))
    assert stored["solution"] == {"code": "x"}


def test_upload_retries_then_succeeds(tmp_path):
    service = FakeService(fail_uploads=2)
    sleeps: list[float] = []
    storage = BlobStorage(
        _config(), service=service, fetcher=None, sleep=sleeps.append
    )
    video = _video(tmp_path / "final.mp4")

    storage.upload_job_bundle("fp", video, None, {"video_url": "u"})

    assert sleeps == [0.5, 1.0]
    assert "videos/fp/final.mp4" in service.store


def test_upload_gives_up_after_the_retries(tmp_path):
    service = FakeService(fail_uploads=99)
    storage = BlobStorage(_config(), service=service, sleep=lambda _seconds: None)
    video = _video(tmp_path / "final.mp4")

    with pytest.raises(ConfigError):
        storage.upload_file(video, "k", "video/mp4")


def test_upload_verifies_the_size(tmp_path):
    class ShrinkingContainer(FakeContainer):
        def upload_blob(self, name, data, overwrite=False, content_settings=None):
            self.store[name] = b"short"
            self.upload_order.append(name)

    service = FakeService()
    service.container = ShrinkingContainer(service.store)
    storage = BlobStorage(_config(), service=service, sleep=lambda _seconds: None)

    with pytest.raises(ConfigError):
        storage.upload_file(_video(tmp_path / "final.mp4"), "k", "video/mp4")


# ---------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------


def test_cache_hit_reads_the_result():
    service = FakeService()
    storage = _storage(service)
    service.store["videos/fp/result.json"] = json.dumps(
        {"video_url": "https://x/final.mp4", "solution": {"code": "c"}}
    ).encode("utf-8")

    cached = storage.get_cached_result("fp")
    assert cached is not None
    assert cached["video_url"] == "https://x/final.mp4"
    assert cached["solution"] == {"code": "c"}


def test_cache_miss_on_missing_or_broken_result():
    service = FakeService()
    storage = _storage(service)
    assert storage.get_cached_result("nope") is None

    service.store["videos/bad/result.json"] = b"not json"
    assert storage.get_cached_result("bad") is None

    service.store["videos/empty/result.json"] = b"{}"
    assert storage.get_cached_result("empty") is None


# ---------------------------------------------------------------------------
# public access check
# ---------------------------------------------------------------------------


def test_public_access_check_passes_and_cleans_up():
    service = FakeService()
    seen: list[str] = []

    def fetcher(url: str):
        seen.append(url)
        return 200, {"Content-Type": "text/plain; charset=utf-8"}, b"pebble public access check"

    storage = _storage(service, fetcher=fetcher)
    ok, detail = storage.check_public_access()

    assert ok is True
    assert "anonymous GET 200" in detail
    assert len(seen) == 1
    assert not any(key.startswith("doctor/") for key in service.store)


def test_public_access_check_reports_what_to_change():
    service = FakeService()
    storage = _storage(service, fetcher=lambda url: (404, {}, b""))
    ok, detail = storage.check_public_access()

    assert ok is False
    assert "not publicly readable" in detail


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def test_missing_container_names_the_variable(monkeypatch):
    # Do not let .env refill the variables this test just removed.
    monkeypatch.setattr("pebble.storage.load_env", lambda: None)
    for name in (
        "AZURE_STORAGE_CONTAINER",
        "AZURE_STORAGE_CONTAINER_NAME",
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_ACCOUNT_NAME",
        "AZURE_STORAGE_ACCOUNT_KEY",
        "AZURE_STORAGE_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ConfigError) as excinfo:
        load_blob_config()
    assert "AZURE_STORAGE_CONTAINER" in str(excinfo.value)
    assert storage_configured() is False


def test_connection_string_wins_over_account_key(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "videos")
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", CONNECTION)
    monkeypatch.delenv("AZURE_STORAGE_ACCOUNT_NAME", raising=False)
    monkeypatch.delenv("AZURE_STORAGE_ACCOUNT_KEY", raising=False)

    config = load_blob_config()
    assert config.container == "videos"
    assert config.connection_string == CONNECTION
    assert storage_configured() is True
    # The repr may be logged: it must not contain the secret itself.
    assert "fake==" not in repr(config)


def test_account_name_and_key_alternative(monkeypatch):
    monkeypatch.setattr("pebble.storage.load_env", lambda: None)
    monkeypatch.delenv("AZURE_STORAGE_PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER_NAME", "pebble")
    monkeypatch.delenv("AZURE_STORAGE_CONTAINER", raising=False)
    monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("AZURE_STORAGE_ACCOUNT_KEY", raising=False)
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "acct")
    monkeypatch.setenv("AZURE_STORAGE_KEY", "secret==")

    config = load_blob_config()
    assert config.container == "pebble"
    assert config.account_name == "acct"
    assert config.public_url("videos/x/final.mp4") == (
        "https://acct.blob.core.windows.net/pebble/videos/x/final.mp4"
    )


def test_anonymous_get_uses_httpx_without_credentials(monkeypatch):
    calls: dict[str, object] = {}

    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "video/mp4"}
        content = b"data"

    def fake_get(url, timeout=None, follow_redirects=False):
        calls["url"] = url
        calls["timeout"] = timeout
        return FakeResponse()

    import httpx

    monkeypatch.setattr(httpx, "get", fake_get)
    status, headers, body = anonymous_get("https://example.com/x.mp4")

    assert status == 200
    assert headers["Content-Type"] == "video/mp4"
    assert body == b"data"
    assert calls["url"] == "https://example.com/x.mp4"
