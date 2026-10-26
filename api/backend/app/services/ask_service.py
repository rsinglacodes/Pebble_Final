"""Service handling DSA problem queries, concept evaluation, and solution retrieval."""

import logging
import re
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.core.dsa_keywords import contains_dsa_keyword, has_prompt_injection
from backend.app.models.ask_history import AskHistory
from backend.app.models.user import User
from backend.app.schemas.ask import (
    AskResponse,
    CandidateInfo,
    ProblemInfo,
    SolutionInfo,
)
from backend.app.schemas.video import CreateVideoJobRequest
from backend.app.services.intent_service import IntentService
from backend.app.services.payload_builder import PayloadBuilder
from backend.app.services.problem_service import ProblemService

logger = logging.getLogger(__name__)

OUT_OF_SCOPE_MESSAGE = (
    "Sorry, I can only help with data structures and algorithms. "
    "Try a LeetCode number, a problem name, or a topic like arrays, trees or graphs."
)
CONCEPT_MESSAGE = "Pebble will generate the explanation from your description."


class AskService:
    """Service handling /ask queries and optional history persistence."""

    def __init__(
        self,
        problem_service: Optional[ProblemService] = None,
        intent_service: Optional[IntentService] = None,
    ):
        self.problem_service = problem_service or ProblemService()
        self.intent_service = intent_service or IntentService()

    def _extract_code_block(self, text: str) -> Tuple[bool, Optional[str], Optional[str], str]:
        """Detect and extract fenced or pasted code blocks.

        Returns:
            Tuple[detected: bool, code: Optional[str], language: Optional[str], remaining_text: str]
        """
        # 1. Fenced code block (```lang ... ```)
        fenced_match = re.search(r"```([a-zA-Z0-9_+-]*)\n?([\s\S]*?)```", text)
        if fenced_match:
            lang = fenced_match.group(1).lower().strip() or None
            if lang in ("c++", "cpp"):
                lang = "cpp"
            elif lang in ("py", "python"):
                lang = "python"
            code = fenced_match.group(2).strip()
            remaining = (text[: fenced_match.start()] + " " + text[fenced_match.end() :]).strip()
            return True, code, lang, remaining

        # 2. Heuristic for pasted code without markdown fences
        py_patterns = [r"\bdef\s+\w+\s*\(.*?\):", r"\bclass\s+\w+[\s:(]"]
        java_cpp_patterns = [
            r"\b(?:public|private|protected)?\s*(?:static)?\s*(?:int|void|boolean|bool|string|vector|List|ListNode|TreeNode)\s+\w+\s*\(",
            r"#include\s+<",
            r"std::vector",
        ]
        all_patterns = py_patterns + java_cpp_patterns

        is_code = any(re.search(pat, text) for pat in all_patterns)
        if is_code:
            detected_lang = "python" if any(re.search(pat, text) for pat in py_patterns) else "cpp"
            return True, text.strip(), detected_lang, ""

        return False, None, None, text

    def _extract_problem_query(self, text: str) -> Optional[str]:
        """Extract candidate problem query from conversational text."""
        raw = text.strip()
        if not raw:
            return None

        # Check LeetCode URL
        url_match = re.search(r"https?://(?:www\.)?leetcode\.com/problems/([^/?#\s]+)", raw, re.IGNORECASE)
        if url_match:
            return url_match.group(0)

        # Check explicit problem number pattern like "problem 1", "leetcode 1", "#1"
        num_match = re.search(r"\b(?:problem|leetcode|question|lc|#)\s*#?\s*(\d+)\b", raw, re.IGNORECASE)
        if num_match:
            return num_match.group(1)

        # Check if text is just an integer
        if raw.isdigit():
            return raw

        # Strip common prompt phrases
        cleaned = re.sub(
            r"\b(?:solve|explain|solution(?:\s+for)?|can\s+you\s+solve|how\s+to\s+solve|code\s+for|in\s+[a-zA-Z0-9#+]+)\b",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip()

        if cleaned.isdigit():
            return cleaned

        return cleaned if cleaned else raw

    def _format_language(self, lang: str) -> str:
        """Format language name for user messages."""
        if lang.lower() in ("cpp", "c++"):
            return "C++"
        return lang.capitalize()

    def _save_history(
        self,
        db: Session,
        user: Optional[User],
        text: str,
        status: str,
        problem_id_int: Optional[int],
        programming_language: Optional[str],
    ) -> None:
        """Record an ask_history entry. Failures are caught and logged."""
        if not user or status == "out_of_scope":
            return

        resolved_problem_uuid = None
        if problem_id_int is not None:
            try:
                prob = self.problem_service.problem_repo.get_by_external_id(db, str(problem_id_int))
                if prob:
                    resolved_problem_uuid = prob.id
            except Exception as e:
                logger.error("Failed to lookup problem for history: %s", type(e).__name__)

        try:
            history_entry = AskHistory(
                user_id=user.id,
                text=text,
                status=status,
                problem_id=resolved_problem_uuid,
                programming_language=programming_language,
            )
            db.add(history_entry)
            db.commit()
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            logger.error("Failed to record ask history: %s", type(e).__name__)

    def _safe_save_history(
        self,
        db: Session,
        user: Optional[User],
        text: str,
        status: str,
        problem_id_int: Optional[int],
        programming_language: Optional[str],
    ) -> None:
        """Wrapper ensuring history recording never raises exceptions."""
        try:
            self._save_history(db, user, text, status, problem_id_int, programming_language)
        except Exception as e:
            logger.error("Failed to record ask history: %s", type(e).__name__)

    def ask(
        self,
        db: Session,
        text: str,
        programming_language: str = "python",
        user: Optional[User] = None,
    ) -> AskResponse:
        """Process an /ask query conforming to status specification.

        Persists to ask_history for valid statuses without raising on DB failure.
        """
        # 1. Prompt Injection rejection (immediate out_of_scope, no lookup)
        if has_prompt_injection(text):
            return AskResponse(
                status="out_of_scope",
                message=OUT_OF_SCOPE_MESSAGE,
                available_languages=[],
                can_generate=False,
            )

        # 2. Pasted Code Handling
        has_code, code_content, code_lang, remaining_text = self._extract_code_block(text)
        if has_code and code_content:
            target_lang = code_lang or programming_language
            user_solution = SolutionInfo(
                language=target_lang,
                code=code_content,
                validated=False,
            )

            # Check if a problem resolves from remaining text or query
            prob_resolved = None
            avail_languages = []
            query_candidate = self._extract_problem_query(remaining_text if remaining_text else text)
            if query_candidate:
                resolve_result = self.problem_service.resolve_problem(
                    db=db, q=query_candidate, language=programming_language
                )
                if resolve_result.resolved and resolve_result.problem:
                    prob_resolved = ProblemInfo(
                        id=resolve_result.problem.id,
                        slug=resolve_result.problem.slug,
                        title=resolve_result.problem.title,
                        source_url=resolve_result.problem.source_url,
                    )
                    avail_languages = resolve_result.available_languages

            if prob_resolved:
                response = AskResponse(
                    status="found",
                    message=f"Found problem '{prob_resolved.title}' for your submitted code.",
                    problem=prob_resolved,
                    solution=user_solution,
                    available_languages=avail_languages,
                    can_generate=True,
                )
                self._safe_save_history(db, user, text, response.status, prob_resolved.id, programming_language)
                return response
            else:
                response = AskResponse(
                    status="concept",
                    message=CONCEPT_MESSAGE,
                    solution=user_solution,
                    available_languages=[],
                    can_generate=True,
                )
                self._safe_save_history(db, user, text, response.status, None, programming_language)
                return response

        # 3. Standard Text Query Processing
        query_candidate = self._extract_problem_query(text)
        query = query_candidate or text.strip()

        resolve_result = self.problem_service.resolve_problem(
            db=db, q=query, language=programming_language
        )

        # Case A: Problem Resolved
        if resolve_result.resolved and resolve_result.problem:
            prob_info = ProblemInfo(
                id=resolve_result.problem.id,
                slug=resolve_result.problem.slug,
                title=resolve_result.problem.title,
                source_url=resolve_result.problem.source_url,
            )

            if resolve_result.solution:
                # found: problem resolved and a stored solution exists for the chosen language
                response = AskResponse(
                    status="found",
                    message=f"Found verified {self._format_language(resolve_result.solution.language)} solution for '{resolve_result.problem.title}'.",
                    problem=prob_info,
                    solution=SolutionInfo(
                        language=resolve_result.solution.language,
                        code=resolve_result.solution.code,
                        validated=True,
                    ),
                    available_languages=resolve_result.available_languages,
                    can_generate=True,
                )
            else:
                # no_solution: problem resolved but not in that language
                lang_disp = self._format_language(programming_language)
                response = AskResponse(
                    status="no_solution",
                    message=f"No stored {lang_disp} solution for this problem. Pebble will generate one with the video.",
                    problem=prob_info,
                    solution=None,
                    available_languages=resolve_result.available_languages,
                    can_generate=True,
                )

            self._safe_save_history(db, user, text, response.status, prob_info.id, programming_language)
            return response

        # 4. LLM Intent Classifier (if enabled)
        settings = get_settings()
        if (settings.INTENT_PROVIDER or "off").strip().lower() != "off":
            classification = self.intent_service.classify(text)
            if classification is not None:
                if classification.intent in ("chitchat", "off_topic"):
                    status_str = "chitchat" if classification.intent == "chitchat" else "out_of_scope"
                    response = AskResponse(
                        status=status_str,
                        message=classification.reply,
                        available_languages=[],
                        can_generate=False,
                    )
                    if status_str != "out_of_scope":
                        self._safe_save_history(db, user, text, status_str, None, programming_language)
                    return response

                if classification.intent == "dsa_problem" and classification.clean_title:
                    clean_res = self.problem_service.resolve_problem(
                        db=db, q=classification.clean_title, language=programming_language
                    )
                    if not clean_res.resolved and " " in classification.clean_title:
                        clean_res = self.problem_service.resolve_problem(
                            db=db, q=classification.clean_title.replace(" ", "-"), language=programming_language
                        )
                    if clean_res.resolved and clean_res.problem:
                        prob_info = ProblemInfo(
                            id=clean_res.problem.id,
                            slug=clean_res.problem.slug,
                            title=clean_res.problem.title,
                            source_url=clean_res.problem.source_url,
                        )
                        v_req = CreateVideoJobRequest(
                            problem_id=clean_res.problem.id,
                            programming_language=programming_language,
                            title=clean_res.problem.title,
                        )
                        if clean_res.solution:
                            v_pl = PayloadBuilder.build_payload(
                                problem_id=clean_res.problem.id,
                                slug=clean_res.problem.slug,
                                title=clean_res.problem.title,
                                code=clean_res.solution.code,
                                programming_language=programming_language,
                                validated=clean_res.solution.validated,
                            )
                            response = AskResponse(
                                status="found",
                                message=f"Found verified {self._format_language(clean_res.solution.language)} solution for '{clean_res.problem.title}'.",
                                problem=prob_info,
                                solution=SolutionInfo(
                                    language=clean_res.solution.language,
                                    code=clean_res.solution.code,
                                    validated=True,
                                ),
                                available_languages=clean_res.available_languages,
                                can_generate=True,
                                video_request=v_req,
                                video_payload=v_pl,
                            )
                        else:
                            v_pl = PayloadBuilder.build_payload(
                                problem_id=clean_res.problem.id,
                                slug=clean_res.problem.slug,
                                title=clean_res.problem.title,
                                programming_language=programming_language,
                            )
                            response = AskResponse(
                                status="no_solution",
                                message=f"No stored {self._format_language(programming_language)} solution for this problem. Pebble will generate one with the video.",
                                problem=prob_info,
                                solution=None,
                                available_languages=clean_res.available_languages,
                                can_generate=True,
                                video_request=v_req,
                                video_payload=v_pl,
                            )
                        self._safe_save_history(db, user, text, response.status, prob_info.id, programming_language)
                        return response

                # algorithm_concept or unresolved dsa_problem
                if classification.intent in ("algorithm_concept", "dsa_problem"):
                    c_title = (classification.clean_title or text)[:300]
                    v_req = CreateVideoJobRequest(
                        text=c_title,
                        programming_language=programming_language,
                    )
                    v_pl = PayloadBuilder.build_payload(
                        text=c_title,
                        programming_language=programming_language,
                    )
                    response = AskResponse(
                        status="concept",
                        message=classification.reply or CONCEPT_MESSAGE,
                        available_languages=[],
                        can_generate=True,
                        video_request=v_req,
                        video_payload=v_pl,
                    )
                    self._safe_save_history(db, user, text, response.status, None, programming_language)
                    return response

        # Case B: Problem NOT Resolved
        # Scope gate: cap text at 300 characters for concept checking
        concept_sample = text[:300]
        if not contains_dsa_keyword(concept_sample):
            return AskResponse(
                status="out_of_scope",
                message=OUT_OF_SCOPE_MESSAGE,
                available_languages=[],
                can_generate=False,
            )

        # Matches DSA keyword: check if it's clarify (several weak matches) or concept
        if (
            resolve_result.candidates
            and len(resolve_result.candidates) >= 2
            and resolve_result.candidates[0].score >= 0.25
        ):
            candidates = [
                CandidateInfo(
                    id=c.problem.id,
                    slug=c.problem.slug,
                    title=c.problem.title,
                )
                for c in resolve_result.candidates[:3]
            ]
            response = AskResponse(
                status="clarify",
                message="Multiple matching problems found. Please clarify your request or select a candidate.",
                candidates=candidates,
                available_languages=[],
                can_generate=False,
            )
            self._safe_save_history(db, user, text, response.status, None, programming_language)
            return response

        # concept: text resolves to no problem but passes the keyword gate
        response = AskResponse(
            status="concept",
            message=CONCEPT_MESSAGE,
            available_languages=[],
            can_generate=True,
        )
        self._safe_save_history(db, user, text, response.status, None, programming_language)
        return response
