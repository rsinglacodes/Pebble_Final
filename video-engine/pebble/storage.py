"""Azure Blob Storage: upload finished videos and serve them from public URLs.

Layout is keyed by the request fingerprint so the worker can answer a repeat
request straight from the blob store without spending LLM, speech or render
time:

    videos/<fingerprint>/final.mp4
    videos/<fingerprint>/metadata.json
    videos/<fingerprint>/result.json   <- written LAST, it marks the video ready

Only the *names* of the environment variables are part of Pebble's contract;
values (connection strings, account keys) are never logged or returned.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from pebble.config import first_env, load_env
from pebble.errors import ConfigError

logger = logging.getLogger(__name__)

CONNECTION_STRING_KEYS = ("AZURE_STORAGE_CONNECTION_STRING",)
ACCOUNT_NAME_KEYS = ("AZURE_STORAGE_ACCOUNT_NAME",)
ACCOUNT_KEY_KEYS = ("AZURE_STORAGE_ACCOUNT_KEY", "AZURE_STORAGE_KEY")
CONTAINER_KEYS = ("AZURE_STORAGE_CONTAINER", "AZURE_STORAGE_CONTAINER_NAME")
PUBLIC_BASE_URL_KEYS = ("AZURE_STORAGE_PUBLIC_BASE_URL",)

VIDEO_PREFIX = "videos"
DOCTOR_PREFIX = "doctor"
RESULT_OBJECT = "result.json"
METADATA_OBJECT = "metadata.json"
VIDEO_OBJECT = "final.mp4"

VIDEO_CONTENT_TYPE = "video/mp4"
JSON_CONTENT_TYPE = "application/json"
PUBLIC_CACHE_CONTROL = "public, max-age=31536000, immutable"
UPLOAD_RETRIES = 3
UPLOAD_BACKOFF = 0.5


@dataclass(frozen=True)
class BlobConfig:
    container: str
    connection_string: str | None = field(default=None, repr=False)
    account_name: str | None = None
    account_key: str | None = field(default=None, repr=False)
    public_base_url: str | None = None

    def __repr__(self) -> str:  # secrets never appear in repr / logs
        return (
            "BlobConfig("
            f"container={self.container!r}, "
            f"connection_string={'set' if self.connection_string else None}, "
            f"account_name={self.account_name!r}, "
            f"account_key={'set' if self.account_key else None}, "
            f"public_base_url={self.public_base_url!r})"
        )

    @property
    def base_url(self) -> str:
        if self.public_base_url:
            return self.public_base_url.rstrip("/")
        if self.account_name:
            return f"https://{self.account_name}.blob.core.windows.net"
        raise ConfigError(
            "cannot build a public blob URL: set one of "
            f"{' or '.join(PUBLIC_BASE_URL_KEYS)} / {' or '.join(ACCOUNT_NAME_KEYS)}"
        )

    @property
    def container_base_url(self) -> str:
        """URL base of the container itself.

        AZURE_STORAGE_PUBLIC_BASE_URL may be written either as the account
        endpoint or already scoped to the container, so the container segment is
        only added when it is not already there.
        """
        base = self.base_url
        if base.endswith(f"/{self.container}"):
            return base
        return f"{base}/{self.container}"

    def public_url(self, key: str) -> str:
        return f"{self.container_base_url}/{key.lstrip('/')}"


def load_blob_config() -> BlobConfig:
    """Read the blob settings from the environment (.env already loaded)."""
    load_env()
    container = first_env(CONTAINER_KEYS)
    if not container:
        raise ConfigError(
            "blob storage is not configured: set "
            f"{' or '.join(CONTAINER_KEYS)} (the container must already exist)"
        )
    connection_string = first_env(CONNECTION_STRING_KEYS)
    account_name = first_env(ACCOUNT_NAME_KEYS)
    account_key = first_env(ACCOUNT_KEY_KEYS)
    if not connection_string and not (account_name and account_key):
        raise ConfigError(
            "blob storage credentials are missing: set "
            f"{' or '.join(CONNECTION_STRING_KEYS)}, or both "
            f"{' or '.join(ACCOUNT_NAME_KEYS)} and {' or '.join(ACCOUNT_KEY_KEYS)}"
        )
    return BlobConfig(
        container=container.strip(),
        connection_string=connection_string,
        account_name=account_name,
        account_key=account_key,
        public_base_url=first_env(PUBLIC_BASE_URL_KEYS),
    )


def build_service(config: BlobConfig) -> Any:
    """Create an Azure BlobServiceClient for this configuration."""
    from azure.storage.blob import BlobServiceClient

    if config.connection_string:
        return BlobServiceClient.from_connection_string(config.connection_string)
    return BlobServiceClient(
        account_url=f"https://{config.account_name}.blob.core.windows.net",
        credential={"account_name": config.account_name, "account_key": config.account_key},
    )


def anonymous_get(url: str, timeout: float = 30.0) -> tuple[int, dict[str, str], bytes]:
    """Anonymous (credential-free) HTTP GET used by the public-access check."""
    import httpx

    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    return response.status_code, dict(response.headers), response.content


class BlobStorage:
    """Thin wrapper over the Azure Blob SDK with retries and a public check."""

    def __init__(
        self,
        config: BlobConfig,
        service: Any | None = None,
        fetcher: Callable[[str], tuple[int, dict[str, str], bytes]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self._service = service
        self._fetcher = fetcher or anonymous_get
        self._sleep = sleep
        self._public_access: bool | None = None

    @classmethod
    def from_env(
        cls,
        service: Any | None = None,
        fetcher: Callable[[str], tuple[int, dict[str, str], bytes]] | None = None,
    ) -> "BlobStorage":
        return cls(load_blob_config(), service=service, fetcher=fetcher)

    @property
    def container(self) -> str:
        return self.config.container

    @property
    def service(self) -> Any:
        if self._service is None:
            self._service = build_service(self.config)
        return self._service

    def _container_client(self) -> Any:
        return self.service.get_container_client(self.container)

    # -- keys ----------------------------------------------------------

    @staticmethod
    def result_key(fingerprint: str) -> str:
        return f"{VIDEO_PREFIX}/{fingerprint}/{RESULT_OBJECT}"

    @staticmethod
    def metadata_key(fingerprint: str) -> str:
        return f"{VIDEO_PREFIX}/{fingerprint}/{METADATA_OBJECT}"

    @staticmethod
    def video_key(fingerprint: str) -> str:
        return f"{VIDEO_PREFIX}/{fingerprint}/{VIDEO_OBJECT}"

    def public_url(self, key: str) -> str:
        return self.config.public_url(key)

    # -- container access ----------------------------------------------

    def try_enable_public_access(self) -> bool:
        """Ask for blob-level anonymous read. Not permitted is not fatal."""

        from azure.storage.blob import PublicAccess

        try:
            self._container_client().set_container_access_policy(
                signed_identifiers={}, public_access=PublicAccess.Blob
            )
        except Exception as exc:  # pragma: no cover - depends on the account
            logger.warning(
                "could not set the container public access level (%s); "
                "continuing, the anonymous check decides",
                type(exc).__name__,
            )
            return False
        return True

    def check_public_access(self) -> tuple[bool, str]:
        """Upload a throwaway blob and fetch it without any credentials."""
        key = f"{DOCTOR_PREFIX}/public-check-{uuid.uuid4().hex}.txt"
        payload = b"pebble public access check"
        self.upload_bytes(
            payload, key, content_type="text/plain; charset=utf-8", cache_control="no-store"
        )
        try:
            status, headers, body = self._fetcher(self.public_url(key))
            content_type = headers.get("Content-Type") or headers.get("content-type") or "?"
            if status == 200 and body.strip() == payload:
                self._public_access = True
                return True, (
                    f"anonymous GET {status} content-type {content_type} "
                    f"({len(body)} bytes) for {key}"
                )
            self._public_access = False
            return False, (
                f"anonymous GET of {key} returned {status} "
                f"({len(body)} bytes); the blob is not publicly readable"
            )
        finally:
            self.delete(key)

    # -- upload ---------------------------------------------------------

    def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str,
        cache_control: str = PUBLIC_CACHE_CONTROL,
        retries: int = UPLOAD_RETRIES,
    ) -> int:
        """Upload bytes, retrying with backoff; returns the verified size."""
        from azure.storage.blob import ContentSettings

        settings = ContentSettings(content_type=content_type, cache_control=cache_control)
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                client = self._container_client()
                client.upload_blob(
                    name=key, data=data, overwrite=True, content_settings=settings
                )
                size = self._remote_size(key)
                if size is not None and size != len(data):
                    raise OSError(
                        f"uploaded size {size} does not match the local {len(data)} bytes"
                    )
                return len(data)
            except Exception as exc:  # noqa: BLE001 - retried below
                last_error = exc
                logger.warning(
                    "upload of %s failed (attempt %d/%d): %s",
                    key,
                    attempt,
                    retries,
                    type(exc).__name__,
                )
                if attempt < retries:
                    self._sleep(UPLOAD_BACKOFF * attempt)
        raise ConfigError(f"could not upload {key} to blob storage: {last_error}")

    def upload_file(
        self,
        path: Path,
        key: str,
        content_type: str,
        cache_control: str = PUBLIC_CACHE_CONTROL,
        retries: int = UPLOAD_RETRIES,
    ) -> int:
        data = Path(path).read_bytes()
        return self.upload_bytes(
            data, key, content_type=content_type, cache_control=cache_control, retries=retries
        )

    def _remote_size(self, key: str) -> int | None:
        try:
            properties = self._container_client().get_blob_client(key).get_blob_properties()
            return int(properties.size)
        except Exception:  # pragma: no cover - best effort verification
            return None

    def delete(self, key: str) -> bool:
        try:
            self._container_client().delete_blob(key)
            return True
        except Exception:  # noqa: BLE001 - deleting is best effort
            return False

    def download_text(self, key: str) -> str | None:
        try:
            blob = self._container_client().get_blob_client(key)
            return blob.download_blob().readall().decode("utf-8")
        except Exception:  # noqa: BLE001 - a missing blob is not an error
            return None

    # -- the video bundle ------------------------------------------------

    def get_cached_result(self, fingerprint: str) -> dict[str, Any] | None:
        """The stored result.json for this fingerprint, or None on a cache miss."""
        text = self.download_text(self.result_key(fingerprint))
        if not text:
            return None
        try:
            payload = json.loads(text)
        except ValueError:
            logger.warning("cached result.json for %s is not valid JSON", fingerprint[:12])
            return None
        if not isinstance(payload, dict) or "video_url" not in payload:
            return None
        return payload

    def upload_job_bundle(
        self,
        fingerprint: str,
        video_path: Path,
        metadata: dict[str, Any] | None,
        result: dict[str, Any],
    ) -> str:
        """Upload video, metadata and (last) result.json; returns the video URL."""
        video_key = self.video_key(fingerprint)
        size = self.upload_file(video_path, video_key, VIDEO_CONTENT_TYPE)
        logger.info(
            "uploaded %s (%.1f MB) -> %s",
            Path(video_path).name,
            size / (1024 * 1024),
            video_key,
        )
        if metadata is not None:
            self.upload_bytes(
                json.dumps(metadata, indent=2, ensure_ascii=False).encode("utf-8"),
                self.metadata_key(fingerprint),
                content_type=JSON_CONTENT_TYPE,
            )
        # Written last: its presence is what makes the blob a cache hit.
        self.upload_bytes(
            json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"),
            self.result_key(fingerprint),
            content_type=JSON_CONTENT_TYPE,
        )
        return self.public_url(video_key)

    # -- helpers ---------------------------------------------------------

    def ready(self) -> tuple[bool, str]:
        """Cheap check that the container exists and is reachable."""
        try:
            self._container_client().get_container_properties()
        except Exception as exc:  # noqa: BLE001
            return False, f"container '{self.container}' is not reachable ({type(exc).__name__})"
        return True, f"container '{self.container}' reachable"


def env_names_hint() -> str:
    """The accepted environment variable names (never their values)."""
    return ", ".join(
        [
            *CONNECTION_STRING_KEYS,
            *ACCOUNT_NAME_KEYS,
            *ACCOUNT_KEY_KEYS,
            *CONTAINER_KEYS,
            *PUBLIC_BASE_URL_KEYS,
        ]
    )


def storage_configured() -> bool:
    """True when blob storage has a container name and credentials."""
    load_env()
    container = first_env(CONTAINER_KEYS)
    if not container:
        return False
    if first_env(CONNECTION_STRING_KEYS):
        return True
    return bool(first_env(ACCOUNT_NAME_KEYS) and first_env(ACCOUNT_KEY_KEYS))


def os_environ_names() -> list[str]:
    """Sorted names of environment variables that look like storage settings."""
    return sorted(name for name in os.environ if name.startswith("AZURE_STORAGE"))
