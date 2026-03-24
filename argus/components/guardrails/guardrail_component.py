from __future__ import annotations

"""
GuardrailComponent — lightweight, dependency-free input/output safety checks.

All checks are individually togglable via GuardrailSettings.
Set guardrails.enabled=false in settings-develop.yaml to bypass everything.

Input checks (run before RAG retrieval):
  - input_toxicity   : keyword-based toxic content detection
  - ban_topics       : configurable list of forbidden topic keywords
  - anonymize_pii    : regex-based email/phone/SSN replacement (modifies query)
  - token_limit      : tiktoken token count limit

Output checks (run after LLM generation):
  - output_toxicity  : keyword-based toxic content detection on the answer
  - client_isolation : blocks if any retrieved chunk belongs to a different client
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

import tiktoken

from argus.settings.settings import GuardrailSettings

logger = logging.getLogger(__name__)

# ── Toxic word list (extend as needed) ────────────────────────────────────────
# Intentionally minimal for a B2B marketing tool — covers harassment/hate speech.
_TOXIC_PATTERNS: List[str] = [
    r"\bkill\b", r"\bmurder\b", r"\bhate\b", r"\bterror\b",
    r"\bviolence\b", r"\bweapon\b", r"\bexplosive\b", r"\bextremis\w*\b",
    r"\bsuicid\w*\b", r"\bself.harm\b",
]
_TOXIC_RE = re.compile("|".join(_TOXIC_PATTERNS), re.IGNORECASE)

# ── PII patterns ───────────────────────────────────────────────────────────────
_PII_RULES: List[tuple[str, str]] = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",        "[EMAIL]"),
    (r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",    "[PHONE]"),
    (r"\b\d{3}-\d{2}-\d{4}\b",                                        "[SSN]"),
    (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b", "[CARD]"),
]


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class GuardrailResult:
    passed: bool
    reason: str = ""
    modified_text: Optional[str] = None   # set by anonymize_pii with the cleaned query


# ── Component ─────────────────────────────────────────────────────────────────

class GuardrailComponent:
    """
    Stateless guardrail runner — constructed once at startup, called per request.

    Usage:
        result = guardrails.check_input(query, client_id)
        if not result.passed:
            return block(result.reason)
        query = result.modified_text or query   # use anonymized version if changed

        result = guardrails.check_output(answer, chunks, client_id)
        if not result.passed:
            return block(result.reason)
    """

    def __init__(self, cfg: GuardrailSettings) -> None:
        self._cfg = cfg
        try:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._tokenizer = None
        logger.info(
            "GuardrailComponent ready — enabled=%s checks=%s",
            cfg.enabled,
            self._active_checks(),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def check_input(self, query: str, client_id: str) -> GuardrailResult:
        """Run all enabled input-side checks. Returns first failure."""
        if not self._cfg.enabled:
            return GuardrailResult(passed=True)

        # 1. Token limit
        if self._cfg.token_limit:
            result = self._check_token_limit(query)
            if not result.passed:
                return result

        # 2. Toxic content
        if self._cfg.input_toxicity:
            result = self._check_toxicity(query, self._cfg.input_toxicity_threshold)
            if not result.passed:
                return result

        # 3. Banned topics
        if self._cfg.ban_topics:
            result = self._check_ban_topics(query)
            if not result.passed:
                return result

        # 4. PII anonymization (non-blocking — modifies query and passes)
        modified_text: Optional[str] = None
        if self._cfg.anonymize_pii:
            modified_text = self._anonymize_pii(query)
            if modified_text != query:
                logger.info("PII anonymized in query for client=%s", client_id)

        return GuardrailResult(passed=True, modified_text=modified_text)

    def check_output(
        self, answer: str, chunks: List[dict], client_id: str
    ) -> GuardrailResult:
        """Run all enabled output-side checks. Returns first failure."""
        if not self._cfg.enabled:
            return GuardrailResult(passed=True)

        # 1. Client isolation — ensure no chunk leaks from another client
        if self._cfg.client_isolation:
            result = self._check_client_isolation(chunks, client_id)
            if not result.passed:
                return result

        # 2. Toxic output
        if self._cfg.output_toxicity:
            result = self._check_toxicity(answer, self._cfg.output_toxicity_threshold)
            if not result.passed:
                return result

        return GuardrailResult(passed=True)

    # ── Internal checks ───────────────────────────────────────────────────────

    def _check_token_limit(self, text: str) -> GuardrailResult:
        if self._tokenizer is None:
            return GuardrailResult(passed=True)
        count = len(self._tokenizer.encode(text))
        if count > self._cfg.token_limit_max:
            return GuardrailResult(
                passed=False,
                reason=f"Query too long ({count} tokens; max {self._cfg.token_limit_max}).",
            )
        return GuardrailResult(passed=True)

    def _check_toxicity(self, text: str, threshold: float) -> GuardrailResult:
        words = text.split()
        if not words:
            return GuardrailResult(passed=True)
        matches = _TOXIC_RE.findall(text)
        score = len(matches) / max(len(words), 1)
        if score >= threshold or len(matches) >= 2:
            logger.warning("Toxicity detected: matches=%s score=%.2f", matches, score)
            return GuardrailResult(
                passed=False,
                reason="Content policy violation: message contains inappropriate content.",
            )
        return GuardrailResult(passed=True)

    def _check_ban_topics(self, text: str) -> GuardrailResult:
        text_lower = text.lower()
        for topic in self._cfg.ban_topics_list:
            if topic.lower() in text_lower:
                logger.warning("Banned topic detected: %r", topic)
                return GuardrailResult(
                    passed=False,
                    reason=f"Query references a restricted topic: '{topic}'.",
                )
        return GuardrailResult(passed=True)

    @staticmethod
    def _anonymize_pii(text: str) -> str:
        for pattern, replacement in _PII_RULES:
            text = re.sub(pattern, replacement, text)
        return text

    @staticmethod
    def _check_client_isolation(chunks: List[dict], client_id: str) -> GuardrailResult:
        # Internal users (client_id="internal") skip isolation — they have all_campaigns access
        if client_id == "internal":
            return GuardrailResult(passed=True)
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            chunk_client = metadata.get("client_id")
            if chunk_client and chunk_client != client_id:
                logger.error(
                    "Client isolation violation: request client=%s, chunk client=%s",
                    client_id, chunk_client,
                )
                return GuardrailResult(
                    passed=False,
                    reason="Response blocked: cross-client data detected.",
                )
        return GuardrailResult(passed=True)

    def _active_checks(self) -> list[str]:
        cfg = self._cfg
        checks = []
        if cfg.input_toxicity:   checks.append("input_toxicity")
        if cfg.ban_topics:       checks.append("ban_topics")
        if cfg.anonymize_pii:    checks.append("anonymize_pii")
        if cfg.token_limit:      checks.append("token_limit")
        if cfg.output_toxicity:  checks.append("output_toxicity")
        if cfg.client_isolation: checks.append("client_isolation")
        return checks
