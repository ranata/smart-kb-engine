import re
import logging
from typing import Callable, List, Optional


class LLMGuardrailEngine:
    """
    Centralized guardrail and sanitization engine for LLM-based systems.

    Supports:
    - Pre-inference input validation & sanitization
    - Post-inference output validation & sanitization
    - Malicious payload detection
    - Prompt injection detection
    - Domain relevance enforcement
    - Delegated PII masking
    """

    DEFAULT_MALICIOUS_PATTERNS = [
        r"\b(exec|eval|compile|pickle)\b",
        r"\b(os\.system|subprocess|Popen)\b",
        r"\b(rm\s+-rf|chmod\s+777|curl\s+http|wget\s+http)\b",
        r"<script\b[^>]*>",
        r"\b(SELECT|INSERT|DELETE|UPDATE|DROP)\b\s+.+\b(FROM|INTO|TABLE)\b",
        r"\b(powershell|cmd\.exe|bash|sh)\b",
    ]

    DEFAULT_PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+all\s+previous\s+instructions",
        r"disregard\s+system\s+prompt",
        r"act\s+as\s+system",
        r"you\s+are\s+now\s+root",
        r"override\s+all\s+policies",
        r"developer\s+mode",
        r"jailbreak",
    ]

    def __init__(
        self,
        pii_masker: Callable[[str], str],
        max_chars: int = 8000,
        max_lines: int = 200,
        allowed_domains: Optional[List[str]] = None,
        malicious_patterns: Optional[List[str]] = None,
        prompt_injection_patterns: Optional[List[str]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.pii_masker = pii_masker
        self.max_chars = max_chars
        self.max_lines = max_lines
        self.allowed_domains = allowed_domains or []

        self.malicious_patterns = malicious_patterns or self.DEFAULT_MALICIOUS_PATTERNS
        self.prompt_injection_patterns = (
            prompt_injection_patterns or self.DEFAULT_PROMPT_INJECTION_PATTERNS
        )

        self.logger = logger or logging.getLogger("llm_guardrail_engine")

    # ============================================================
    # Public APIs
    # ============================================================

    def guard_input(self, text: str) -> str:
        """
        Apply guardrails before LLM invocation.
        """
        return self._guard(text, phase="input")

    def guard_output(self, text: str) -> str:
        """
        Apply guardrails after LLM inference.
        """
        return self._guard(text, phase="output")

    # ============================================================
    # Core Guardrail Pipeline
    # ============================================================

    def _guard(self, text: str, phase: str) -> str:
        try:
            self._validate_text_input(text, phase)
            self._validate_size_and_structure(text, phase)
            self._detect_malicious_payload(text, phase)
            self._detect_prompt_injection(text, phase)
            self._validate_domain_scope(text, phase)

            sanitized = self.pii_masker(text)
            return sanitized

        except ValueError as exc:
            self._log_failure(exc, phase)
            raise

    # ============================================================
    # Validation Methods
    # ============================================================

    def _validate_text_input(self, text: str, phase: str) -> None:
        if not isinstance(text, str):
            raise ValueError(f"{phase}: input must be text")

        if "\x00" in text:
            raise ValueError(f"{phase}: binary content detected")

        if len(text) > 200 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", text):
            raise ValueError(f"{phase}: encoded payload detected")

        if not re.fullmatch(r"[\x09\x0A\x0D\x20-\x7E]+", text):
            raise ValueError(f"{phase}: non-printable characters detected")

    def _validate_size_and_structure(self, text: str, phase: str) -> None:
        if len(text) > self.max_chars:
            raise ValueError(f"{phase}: input exceeds maximum length")

        if text.count("\n") > self.max_lines:
            raise ValueError(f"{phase}: excessive line breaks detected")

        if text.count("{") > 100 or text.count("<") > 100:
            raise ValueError(f"{phase}: suspicious nested structure detected")

    def _detect_malicious_payload(self, text: str, phase: str) -> None:
        for pattern in self.malicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError(f"{phase}: malicious payload detected")

    def _detect_prompt_injection(self, text: str, phase: str) -> None:
        lowered = text.lower()
        for pattern in self.prompt_injection_patterns:
            if re.search(pattern, lowered):
                raise ValueError(f"{phase}: prompt injection attempt detected")

    def _validate_domain_scope(self, text: str, phase: str) -> None:
        if not self.allowed_domains:
            return

        lowered = text.lower()
        if not any(domain.lower() in lowered for domain in self.allowed_domains):
            raise ValueError(f"{phase}: input outside allowed domain scope")

    # ============================================================
    # Logging
    # ============================================================

    def _log_failure(self, exc: Exception, phase: str) -> None:
        self.logger.warning(
            "LLM guardrail violation",
            extra={
                "phase": phase,
                "reason": str(exc),
                "control": "pre_post_inference_guardrails",
            },
        )
