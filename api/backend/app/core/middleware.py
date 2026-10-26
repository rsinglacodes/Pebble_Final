"""Custom application middlewares for request hardening."""

from fastapi import status
from fastapi.responses import JSONResponse

MAX_BODY_SIZE_BYTES = 200 * 1024  # 200 KB = 204,800 bytes


class BodySizeExceededError(Exception):
    """Exception raised internally when streamed body exceeds allowed limit."""
    pass


class BodySizeLimitMiddleware:
    """ASGI middleware enforcing a strict 200 KB request body size limit."""

    def __init__(self, app, max_bytes: int = MAX_BODY_SIZE_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. Header-based inspection
        headers = dict(scope.get("headers", []))
        content_length_header = headers.get(b"content-length")
        if content_length_header:
            try:
                if int(content_length_header.decode()) > self.max_bytes:
                    response = JSONResponse(
                        status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE),
                        content={
                            "error": "payload_too_large",
                            "message": f"Request body exceeds maximum allowed size of {self.max_bytes // 1024} KB",
                        },
                    )
                    await response(scope, receive, send)
                    return
            except ValueError:
                pass

        # 2. Streaming chunks inspection
        total_bytes = 0

        async def limited_receive():
            nonlocal total_bytes
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                total_bytes += len(body)
                if total_bytes > self.max_bytes:
                    raise BodySizeExceededError()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except BodySizeExceededError:
            response = JSONResponse(
                status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE),
                content={
                    "error": "payload_too_large",
                    "message": f"Request body exceeds maximum allowed size of {self.max_bytes // 1024} KB",
                },
            )
            await response(scope, receive, send)
