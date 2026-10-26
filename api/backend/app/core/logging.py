"""Logging sanitization and security filters preventing leakage of secrets and sensitive data."""

import logging
import re
from typing import Any

# Patterns matching sensitive information
SENSITIVE_PATTERNS = [
    # JWT tokens
    (re.compile(r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+"), "[REDACTED_JWT_TOKEN]"),
    # Bearer authorization headers
    (re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]+", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    # Passwords in JSON or key-value pairs
    (re.compile(r'("(?:password|password_hash|new_password|secret|key)"\s*:\s*)"[^"]*"', re.IGNORECASE), r'\1"[REDACTED]"'),
    (re.compile(r'((?:password|secret|api_key)\s*=\s*)[^\s,]+', re.IGNORECASE), r'\1[REDACTED]'),
    # Database connection strings with credentials
    (re.compile(r"(postgres(?:ql)?(?:\+psycopg)?://[^:]+:)[^@]+(@)", re.IGNORECASE), r"\1[REDACTED]\2"),
    # Long code blocks (e.g., code=... or "code": "...")
    (re.compile(r'("(?:code|user_code)"\s*:\s*)"(?:[^"\\]|\\.){80,}"', re.DOTALL), r'\1"[REDACTED_FULL_USER_CODE]"'),
    # Request text field redaction
    (re.compile(r'("(?:text)"\s*:\s*)"(?:[^"\\]|\\.)*"', re.DOTALL), r'\1"[REDACTED_TEXT]"'),
    (re.compile(r"('(?:text)'\s*:\s*)'[^']*'", re.DOTALL), r"\1'[REDACTED_TEXT]'"),
    (re.compile(r"\btext=([^\s,)]+)", re.IGNORECASE), r"text=[REDACTED_TEXT]"),
]


class SensitiveDataFilter(logging.Filter):
    """Logging filter that scrubs secrets, credentials, tokens, and full code from all log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = self._sanitize_dict(record.args)
            elif isinstance(record.args, (tuple, list)):
                sanitized_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        s_arg = arg
                        for pattern, replacement in SENSITIVE_PATTERNS:
                            s_arg = pattern.sub(replacement, s_arg)
                        sanitized_args.append(s_arg)
                    elif isinstance(arg, dict):
                        sanitized_args.append(self._sanitize_dict(arg))
                    else:
                        sanitized_args.append(arg)
                record.args = tuple(sanitized_args) if isinstance(record.args, tuple) else sanitized_args

        return True

    def _sanitize_dict(self, d: dict) -> dict:
        """Recursively redact sensitive keys in dictionaries."""
        clean = {}
        for k, v in d.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in ("password", "secret", "token", "api_key")):
                clean[k] = "[REDACTED]"
            elif k_lower == "text":
                clean[k] = "[REDACTED_TEXT]"
            elif k_lower in ("code", "user_code") and isinstance(v, str) and len(v) > 60:
                clean[k] = f"{v[:20]}... [FULL_CODE_REDACTED {len(v)} chars]"
            elif isinstance(v, dict):
                clean[k] = self._sanitize_dict(v)
            else:
                clean[k] = v
        return clean


def setup_secure_logging() -> None:
    """Attach SensitiveDataFilter to root and application loggers."""
    log_filter = SensitiveDataFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(log_filter)

    # Attach to root logger itself
    root_logger.addFilter(log_filter)
    logging.getLogger("backend").addFilter(log_filter)
    logging.getLogger("uvicorn").addFilter(log_filter)
