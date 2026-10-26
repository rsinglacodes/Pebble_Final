"""Payload builder constructing the exact JSON contract defined in docs/video-contract.md."""

from typing import Any, Dict, Optional


class PayloadBuilder:
    """Builds the exact JSON payload for POST {VIDEO_ENGINE_URL}/generate-video."""

    @classmethod
    def build_payload(
        cls,
        problem_id: Optional[int] = None,
        slug: Optional[str] = None,
        title: Optional[str] = None,
        code: Optional[str] = None,
        programming_language: str = "python",
        validated: Optional[bool] = None,
        text: Optional[str] = None,
        explanation_language: Optional[str] = None,
        explanation_style: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct the exact video rendering JSON payload.

        Payload Cases:
        (a) stored repo code:
            question: {id, slug, title}
            solution: {code, programming_language, validated: true}
        (b) user code:
            question: {id, slug, title} (or {id: null, slug: null, title: <text>} if unmatched)
            solution: {code, programming_language, validated: false}
        (c) problem known but no code in that language:
            question: {id, slug, title}
            solution: {programming_language} (no code key)
        (d) unmatched text:
            question: {id: null, slug: null, title: <text>}
            solution: {programming_language} (or if user code: {code, programming_language, validated: false})

        Preferences are ALWAYS:
            {explanation_language: 'English', explanation_style: 'beginner_friendly'}
        """
        # 1. Question object
        if problem_id is not None:
            question_data: Dict[str, Any] = {
                "id": problem_id,
                "slug": slug or "",
                "title": title or f"Problem {problem_id}",
            }
        else:
            unmatched_title = text if text is not None else title
            question_data = {
                "id": None,
                "slug": None,
                "title": unmatched_title or "",
            }

        # 2. Solution object
        lang = (programming_language or "python").lower().strip()
        if code and code.strip():
            solution_data: Dict[str, Any] = {
                "code": code.strip(),
                "programming_language": lang,
                "validated": bool(validated),
            }
        else:
            solution_data = {
                "programming_language": lang,
            }

        # 3. Preferences object (always English and beginner_friendly)
        preferences_data = {
            "explanation_language": "English",
            "explanation_style": "beginner_friendly",
        }

        return {
            "question": question_data,
            "solution": solution_data,
            "preferences": preferences_data,
        }
