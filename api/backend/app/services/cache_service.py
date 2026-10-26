"""Internal cache key computation service for video reuse and deduplication."""

import hashlib
from typing import Optional


class CacheService:
    """Computes internal sha256 cache keys conforming to docs/video-contract.md."""

    @staticmethod
    def compute_cache_key(
        problem_id: Optional[int] = None,
        text: Optional[str] = None,
        title: Optional[str] = None,
        programming_language: str = "python",
        user_code: Optional[str] = None,
        is_user_code: bool = False,
        explanation_language: Optional[str] = None,
        explanation_style: Optional[str] = None,
    ) -> str:
        """Compute the unique internal cache key.

        Formula:
        sha256(problem_identifier + ":" + programming_language + ":" + user_code_hash)

        Where:
        - problem_identifier = problem number (as string) or normalized lowercase text for unmatched.
        - programming_language = normalized lowercase language.
        - user_code_hash = sha256(user_code) if user code is present, else empty string.
        - Explanation language and style are removed from the key.
        """
        # 1. Problem Identifier: problem number or normalized lowercase text
        if problem_id is not None:
            problem_identifier = str(problem_id)
        else:
            raw_text = text if text is not None else title
            problem_identifier = (raw_text or "").strip().lower()

        # 2. Programming Language
        lang_token = (programming_language or "python").strip().lower()

        # 3. User Code Hash
        if (is_user_code or user_code) and user_code and user_code.strip():
            user_code_hash = hashlib.sha256(user_code.strip().encode("utf-8")).hexdigest()
        else:
            user_code_hash = ""

        # 4. Hash combination
        raw_key = f"{problem_identifier}:{lang_token}:{user_code_hash}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
