"""Rate limiting setup using slowapi with per-user authentication keying."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_user_or_ip(request: Request) -> str:
    """Extract user identifier from JWT Bearer token if present, else fallback to client IP."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth[7:].strip()
        try:
            user_id = decode_access_token(token)
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
        return f"token:{token[:16]}"
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_or_ip)
